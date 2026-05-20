"""SiliconFlow image generation backend.

Uses SiliconFlow Kolors model (free, supports Chinese prompts).
API is OpenAI-compatible.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    success_response,
)

logger = logging.getLogger(__name__)

_MODELS = {
    "Kwai-Kolors/Kolors": {
        "display": "Kolors (Free)",
        "speed": "~5-10s",
        "strengths": "Free, Chinese prompt support",
    },
    "flux-schnell": {
        "display": "FLUX Schnell (Free)",
        "speed": "~3-5s",
        "strengths": "Fast, free tier",
    },
    "stable-diffusion-xl": {
        "display": "SDXL (Free)",
        "speed": "~5-8s",
        "strengths": "Classic, free tier",
    },
}

DEFAULT_MODEL = "Kwai-Kolors/Kolors"

_SIZE_MAP = {
    "landscape": "1280x720",
    "square": "1024x1024",
    "portrait": "720x1280",
}


class SiliconFlowImageGenProvider(ImageGenProvider):

    @property
    def name(self) -> str:
        return "siliconflow"

    @property
    def display_name(self) -> str:
        return "SiliconFlow"

    def is_available(self) -> bool:
        return bool(os.getenv("SILICONFLOW_API_KEY"))

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": mid, "display": m.get("display", mid),
             "speed": m.get("speed", ""), "strengths": m.get("strengths", "")}
            for mid, m in _MODELS.items()
        ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "SiliconFlow",
            "badge": "free",
            "tag": "Free image generation, supports Chinese prompts",
            "env_vars": [
                {"key": "SILICONFLOW_API_KEY", "prompt": "SiliconFlow API Key",
                 "url": "https://cloud.siliconflow.cn"},
            ],
        }

    def generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO,
                 **kwargs: Any) -> Dict[str, Any]:
        api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        if not api_key:
            return error_response(
                error="SILICONFLOW_API_KEY not set",
                error_type="missing_api_key", provider="siliconflow",
                aspect_ratio=aspect_ratio)

        model = kwargs.get("model") or DEFAULT_MODEL
        aspect = resolve_aspect_ratio(aspect_ratio)
        image_size = _SIZE_MAP.get(aspect, "1024x1024")

        payload = {
            "model": model,
            "prompt": prompt.strip(),
            "image_size": image_size,
            "num_inference_steps": 25,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                "https://api.siliconflow.cn/v1/images/generations",
                headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else 0
            try:
                err = exc.response.json().get("error", {}).get("message", str(exc))
            except Exception:
                err = str(exc)
            return error_response(
                error=f"SiliconFlow API error ({status}): {err}",
                error_type="api_error", provider="siliconflow",
                model=model, prompt=prompt, aspect_ratio=aspect)
        except requests.Timeout:
            return error_response(
                error="SiliconFlow timed out (120s)",
                error_type="timeout", provider="siliconflow",
                model=model, prompt=prompt, aspect_ratio=aspect)

        result = resp.json()
        images = result.get("images") or result.get("data") or []
        if not images:
            return error_response(
                error="No images returned", error_type="empty_response",
                provider="siliconflow", model=model, prompt=prompt,
                aspect_ratio=aspect)

        url = images[0].get("url", "")
        if not url:
            return error_response(
                error="No URL in response", error_type="empty_response",
                provider="siliconflow", model=model, prompt=prompt,
                aspect_ratio=aspect)

        return success_response(
            image=url, model=model, prompt=prompt,
            aspect_ratio=aspect, provider="siliconflow")


def register(ctx: Any) -> None:
    ctx.register_image_gen_provider(SiliconFlowImageGenProvider())
