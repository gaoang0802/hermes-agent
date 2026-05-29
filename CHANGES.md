# Hermes Agent Fork 完整变更记录

本文件记录 `gaoang0802/hermes-agent` fork 相对于上游 `NousResearch/hermes-agent`
的所有本地修改。按时间倒序排列，最早追溯到 2026年4月。

---

## 总览

| 类别 | 条目 | 说明 |
|------|------|------|
| 🏗️ 基础设施 | 7 个 | 启动脚本、自动补丁、路由链、智能路由、补丁锁、备份机制、自检集成 |
| 💰 成本优化 | 2 个 | _SUMMARY_RATIO 降低、压缩效率日志 |
| 🌐 中文化 | 7 轮 | 45+ run_agent key、16 locale × 331 keys |
| 🐛 Bug 修复 | 1 个 | background_review_callback 竞态条件 |
| ⚙️ 配置 | 3 个 | config.yaml、SOUL.md、.env |
| 🔧 自定义脚本 | 2 个 | 新闻抓取、硅基流动图片生成 |
| 🧪 测试覆盖 | 21 项 | 8 个测试类覆盖全部补丁、版本检查、锁机制 |

---

## 六、补丁系统重构 (2026-05-21)

**涉及文件：**
- `~/.hermes/apply_hermes_patch.py` — 重写（158 → 430 行）
- `~/.hermes/test_patches.py` — 新建（480 行）
- `~/.hermes/hermes-start.sh` — 更新（自检集成 + 4 阶段流程）

### 6.1 补丁机制全面升级

| 改进项 | 之前 | 之后 |
|--------|------|------|
| 效率日志插入方式 | 硬编码字符串匹配 (`old_block in content`) | 正则匹配 (`re.compile`)，容忍变量名/缩进变化 |
| 上游版本感知 | 无 | 从 `pyproject.toml` 解析版本，与 `HERMES_PATCH_VERSION=(0,14,0)` 比对 |
| 写入安全 | 直接 `open(..., "w")` overwrite | `_backup_file()` 备份 + `.patch_tmp` 临时文件 + `os.replace` 原子替换 |
| 并发防护 | 无 | `_acquire_lock()` — fcntl 文件锁 + PID 文件回退 |
| 完整性验证 | 无 | `_validate_patch_content()` 检查标记存在 + 上下文完整性 |
| 标记不完整处理 | 无感知 | 检测后自动移除旧标记并重新插入 |

### 6.2 测试覆盖

`test_patches.py` — 8 个测试类、21 项测试：

| 测试类 | 覆盖场景 |
|--------|---------|
| `TestVersionCheck` | pyproject 版本解析、匹配/不匹配 |
| `TestBackupAndSafeWrite` | 备份创建、原子写入、文件不存在 |
| `TestPatchCli` | 干净文件、幂等性、不完整标记重应用 |
| `TestPatchContextCompressor` | 比率修改、效率日志、v0.15 兼容 |
| `TestPatchGatewayBanner` | 汉化、幂等性 |
| `TestLockMechanism` | 获取释放、双重获取拒绝 |
| `TestValidatePatchContent` | 完整/不完整补丁验证 |
| `TestMainEntry` | 全流程集成测试 |

运行方式：`python3 ~/.hermes/apply_hermes_patch.py --self-test`

### 6.3 启动流程变更

| 阶段 | 之前 | 之后 |
|------|------|------|
| 启动步骤数 | `[0/3]-[3/3]` | `[0/4]-[4/4]` |
| 补丁自检 | 无 | 阶段 0 先跑 21 项测试，通过才应用补丁 |
| 降级策略 | 无 | 自检失败跳过补丁，继续启动（风险自负） |
| CLI 入口 | `start|stop|restart` | 新增 `self-test` 子命令 |

---

## 一、基础设施

### 1.1 hermes-start.sh（一键启动）

**位置：** `~/.hermes/hermes-start.sh`（~120 行）

**功能：**
- `clean_env()` — 清除 Windows 泄漏到 WSL 的代理变量（`http_proxy` 等），防止 API 调用走错代理
- 端口管理 — 自动释放 4000、4001、8642 端口
- 自动补丁 — 每次启动调用 `apply_hermes_patch.py`
- 路由链启动 — LiteLLM(:4001) → Token Router(:4000)
- 导出 `HERMES_COMPRESSION_SUMMARY_RATIO=0.08` 环境变量

**用法：** `hermes-start [start|stop|restart]`

### 1.2 apply_hermes_patch.py（自动补丁系统）

**位置：** `~/.hermes/apply_hermes_patch.py`（~170 行）

**设计目标：** `hermes update` 会重置源码文件，此脚本在每次启动时重新应用修改，确保自定义不丢失。

**补丁清单：**
1. **cli.py** — 插入 `HERMES_TOKEN_OPT` 代码块，运行时通过环境变量覆盖 `_SUMMARY_RATIO`
2. **context_compressor.py** — `_SUMMARY_RATIO 0.20 → 0.08` + 压缩效率日志
3. **gateway.py** — 启动横幅汉化

所有补丁幂等，重复运行不会出错。

### 1.3 LiteLLM 路由链

**位置：** `~/.hermes/litellm/`

| 文件 | 行数 | 用途 |
|------|------|------|
| `config.deepseek.yaml` | 21 | DeepSeek Flash/Pro 模型配置（API key、base URL） |
| `token_router.py` | 291 | 令牌路由 — Hermes 请求 :4000，路由到 :4001 的 LiteLLM |
| `router_callback.py` | 47 | 路由回调 — 请求/响应日志 |
| `start-router.sh` | 42 | 一键启动 LiteLLM + Token Router |

**架构：** `Hermes → :4000 (Token Router) → :4001 (LiteLLM) → DeepSeek API`

### 1.4 smart_router.py（智能路由代理）

**位置：** `~/.hermes/smart_router.py`（151 行）

**用途：** 按任务复杂度分流——简单任务走本地 Ollama（免费），复杂任务走 DeepSeek API。
通过关键词匹配（debug、error、refactor 等）判断复杂度。

**当前状态：** 未启用（LiteLLM 路由链直接接管 :4000，此脚本是备用方案）。

---

## 二、成本优化

### 2.1 _SUMMARY_RATIO 降低（2026-05-16）

**文件：** `agent/context_compressor.py`

**变更：** `_SUMMARY_RATIO 0.20 → 0.08`

**效果：** 压缩摘要输出 token 减少 60%，预计节省 ¥9/天。
通过 `hermes-start.sh` 中的环境变量 `HERMES_COMPRESSION_SUMMARY_RATIO=0.08`
和 `apply_hermes_patch.py` 双重保障，`hermes update` 后自动恢复。

**注意：** 曾尝试 0.05 但导致压缩输出≈输入（死循环），0.08 是安全底线。

### 2.2 压缩效率日志（2026-05-19）

**文件：** `agent/context_compressor.py`

**新增：** 每次压缩完成后输出效率指标：
```
Compression efficiency: 🟢 8.5:1 (saved=34000 input, cost=4000 output tokens)
```
- 🟢 ≥5:1（高效）
- 🟡 3-5:1（中等）
- 🔴 <3:1（低效）

---

## 三、中文化 (i18n)

### 3.1 第一轮：框架基础（2026-05-19）

**提交：** `5ad37e0db`

- `run_agent.py`: 29 处 `_emit_status()` 硬编码英文 → `t()` 调用
- `gateway/run.py`: shutdown/restart/elapsed/iteration/running 状态改用 `t()`
- 16 个 locale 文件新增 `run_agent` 段（31 keys）+ `gateway` 段（9 keys）
- `zh.yaml`: 完整中文翻译

### 3.2 第二轮：补充遗漏（2026-05-19）

**提交：** `251a99dde`

- `agent/conversation_compression.py`: 3 处 `_emit_warning()` → `t()`
- `agent/background_review.py`: self-improvement review → `t()`
- `agent/tool_executor.py`: tool completed → `t()`
- 新增 4 个 locale key：`compression_aborted`、`compression_summary_failed`、`compression_aux_failed`、`tool_completed`

### 3.3 审批消息翻译（2026-05-19）

**提交：** `980225045`

- `gateway/run.py`: 审批请求消息改用 `t("gateway.approval_text_prompt")`
- 修复 14 个非 en/zh locale 文件缺失 `gateway.approval_text_prompt`

### 3.4 上下文压缩消息修复（2026-05-19）

**提交：** `fdc824c35`

- `run_agent.py` / `agent/conversation_loop.py`: `compacting_context` 字符串改用 `t()`

### 3.5 第三轮：_emit_status 全覆盖（2026-05-20）

**提交：** `834639057`

`run_agent.py` 中 13 处遗漏的 `_emit_status()` → `t()`：

| Key | 中文示例 |
|-----|---------|
| `no_response_aborting` | 提供商在 {elapsed}秒内无响应，中止调用 |
| `stream_malformed_data` | 提供商返回了格式异常的流数据 |
| `stream_connection_failed` | 与提供商的连接失败 |
| `no_response_reconnecting` | 提供商无响应，重新连接中 |
| `primary_failed_switch_fallback` | 主模型失败，切换到备用 |
| `stale_connections_cleaned` | 检测到过期连接，已清理 |
| `context_reduced_retrying` | 上下文已缩减至 {reduced} tokens |
| `tool_guardrail_halted` | 工具护栏停止 {tool_name} |
| `stream_interrupted_use_delivered` | 数据流中断，使用已接收内容 |
| `iteration_budget_exhausted` | 迭代预算已耗尽 |
| `compression_provider_unavailable` | 配置的压缩提供商不可用 |
| `compression_no_provider` | 未配置辅助 LLM 提供商 |
| `compression_model_context_low` | 压缩模型上下文不足，自动降低阈值 |
| `nous_rate_limit` | Nous 限速 |

### 3.6 网关启动横幅（2026-05-20）

**提交：** `dc1234010`

`hermes_cli/gateway.py`:
```
"Hermes Gateway Starting..."     → "Hermes 网关启动中…"
"Messaging platforms + cron"     → "消息平台 + 定时任务调度"
"Press Ctrl+C to stop"           → "Ctrl+C 停止"
```

### 3.7 当前状态

- **16 个 locale 文件** 全部同步（331 keys each）
- **en.yaml** + **zh.yaml** 完整翻译
- **其余 14 个文件** 使用英文作为 fallback（有 i18n 测试保障一致性）

---

## 四、Bug 修复

### 4.1 background_review_callback 竞态条件（2026-05-20）

**提交：** `7baea7147`

**症状：** 微信间歇出现 `⚠ 辅助任务 后台审核 失败: 'Thread' object is not callable`

**根因：** gateway 在主线程设置 `agent.background_review_callback`，
而 bg-review 线程异步读取。竞态条件下回调被覆盖为 Thread 对象。

**修复：** `run_agent.py` + `agent/background_review.py` 回调调用前加 `callable()` 检查。

```python
# Before
if _bg_cb:
    _bg_cb(message)
# After
if _bg_cb and callable(_bg_cb):
    _bg_cb(message)
```



## 五、配置

### 5.1 config.yaml

**位置：** `~/.hermes/config.yaml`

**关键配置：**
```yaml
auxiliary:
  compression:
    base_url: http://localhost:4000/v1   # 走本地路由链
    model: flash                          # deepseek-v4-flash
    provider: custom
```

### 4.2 SOUL.md（AI 人格）

**位置：** `~/.hermes/SOUL.md`（215 行）

**用途：** 为 Hermes 赋予个性化设定——"昂哥的专属助手"，包含语气、偏好、知识范围等。

### 4.3 .env

**位置：** `~/.hermes/.env`

**内容：** API 密钥、模型配置等环境变量。

---

## 七、自定义脚本

### 5.1 fetch_news.py

**位置：** `~/.hermes/scripts/fetch_news.py`（59 行）

新闻抓取脚本。

### 5.2 siliconflow_image.py

**位置：** `~/.hermes/scripts/siliconflow_image.py`（40 行）

硅基流动（SiliconFlow）图片生成 API 调用脚本。

---

## 八、维护指南

### `hermes update` 升级后检查清单

1. 重启 Hermes（`hermes-start restart`）— `apply_hermes_patch.py` 会自动恢复补丁
2. 验证 `_SUMMARY_RATIO`：`grep _SUMMARY_RATIO ~/.hermes/hermes-agent/agent/context_compressor.py`
3. 发微信测试翻译是否生效
4. 检查压缩效率日志是否正常输出

### 新增英文消息时的操作

1. `grep '_emit_status\|_safe_print.*[' ~/.hermes/hermes-agent/run_agent.py` 查找遗漏
2. 先改 `locales/en.yaml` → `locales/zh.yaml`
3. 运行 `python ~/.hermes/hermes-agent/_validate_locales.py`（如存在）确保 16 文件一致
4. 同步到 WSL：`wsl cp /mnt/c/Users/高昂/hermes-agent-fork/... /home/gaoang/.hermes/hermes-agent/...`

### 文件变更追踪速查

| 目的 | 文件 | 优先级 |
|------|------|--------|
| 翻译主文件 | `run_agent.py` | 🔴 每次升级必查 |
| 压缩参数 | `agent/context_compressor.py` | 🔴 每次升级必查 |
| 压缩警告翻译 | `agent/conversation_compression.py` | 🟡 |
| 启动横幅 | `hermes_cli/gateway.py` | 🟢 |
| 工具/审批翻译 | `agent/tool_executor.py`、`agent/background_review.py` | 🟢 |
| 所有 locale | `locales/*.yaml` | 🔴 新增 key 时 |
| 启动脚本 | `~/.hermes/hermes-start.sh` | 独立于代码更新 |
| 补丁脚本 | `~/.hermes/apply_hermes_patch.py` | 独立于代码更新 |
| 补丁测试 | `~/.hermes/test_patches.py` | 🟢 新增 key 时更新 |
| 补丁自检 | `~/.hermes/hermes-start.sh` `self-test` | 🟢 修改补丁逻辑后运行 |

---

> **最后更新：** 2026-05-21
> **维护者：** 高昂 <258218691@qq.com>
> **仓库：** https://ghfast.top/https://github.com/gaoang0802/hermes-agent (branch: `i18n-zh-v2`)
