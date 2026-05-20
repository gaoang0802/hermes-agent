"""SiliconFlow provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

siliconflow = ProviderProfile(
    name="siliconflow",
    aliases=("silicon",),
    default_aux_model="Qwen/Qwen3-32B",
    env_vars=("SILICONFLOW_API_KEY",),
    base_url="https://api.siliconflow.cn/v1",
)

register_provider(siliconflow)
