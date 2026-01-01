# Gemini Reverse API 接口文档

**版本**: v3.1 | **最后更新**: 2025-12-26

## 服务信息

| 项目 | 值 |
|------|-----|
| 基础URL | `https://google-api.aihang365.com` |
| 认证 | 无需API Key（服务端Cookie认证） |
| 内容类型 | `application/json` |
| 核心特性 | 自动去水印、智能重试、2并发、断点续传 |

---

## 快速开始

```bash
# 文本对话（默认使用 gemini-3-flash-preview）
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-3-flash-preview", "messages": [{"role": "user", "content": "你好"}]}'

# 图片生成（自动去水印）
curl -X POST https://google-api.aihang365.com/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cute cat", "response_type": "url"}'
```

---

## 模型列表

### GET /api/models

获取所有支持的模型列表。

```bash
curl https://google-api.aihang365.com/api/models
```

**响应**:
```json
{
  "models": [
    {"id": "gemini-3-flash-preview", "name": "Gemini 3.0 Flash", "description": "最新快速模型"},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "日常对话"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "高阶数学和代码"},
    {"id": "gemini-3.0-pro", "name": "Gemini 3.0 Pro", "description": "最新Pro模型"},
    {"id": "gemini-2.5-flash-image", "name": "Flash Image", "description": "快速图片生成"},
    {"id": "gemini-3-pro-image-preview", "name": "Pro Image", "description": "高质量图片 2048x2048"},
    {"id": "gemini-3-pro-image-preview-2k", "name": "Pro Image 2K", "description": "2K高清图片"},
    {"id": "gemini-3-pro-image-preview-4k", "name": "Pro Image 4K", "description": "4K超高清图片"}
  ],
  "categories": {
    "text": [...],
    "image": [...]
  },
  "default": "gemini-3-flash-preview"
}
```

### 文本模型

| 模型 ID | 说明 | 特点 | 推荐场景 |
|---------|------|------|---------|
| **gemini-3-flash-preview** | **默认模型** | 最新版本，响应极快，逻辑推理能力强 | 日常对话、快速问答 |
| gemini-3.0-pro | 增强版模型 | 适合处理极长上下文和复杂逻辑 | 高级推理、复杂任务 |
| gemini-2.5-pro | 稳定版专家模型 | 具备深度思考能力 | 复杂推理、代码生成 |
| gemini-2.5-flash | 高性价比模型 | 兼顾性能与响应速度 | 快速生成 |

### 图片模型

| 模型 ID | 分辨率 | 生成速度 | 适用场景 |
|---------|--------|---------|---------|
| gemini-2.5-flash-image | 1024x1024 | ⚡⚡⚡ (~30s) | 快速生成、草图预览 |
| gemini-3-pro-image-preview | 2048x2048 | ⚡⚡ (~60s) | 高质量、细节丰富 |
| gemini-3-pro-image-preview-2k | 2560x1440+ | ⚡ (~60s) | 2K高清、设计素材 |
| gemini-3-pro-image-preview-4k | 4096x4096 | ⚡ (~90s) | 4K超高清、专业级画质 |

---

## 文本生成

### POST /v1/chat/completions (OpenAI兼容)

OpenAI 格式对话接口，默认使用 `gemini-3-flash-preview`。

**参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model | string | 否 | "gemini-3-flash-preview" | 模型ID |
| messages | array | 是 | - | 对话历史 |

**示例**:

```bash
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{"role": "user", "content": "帮我写一段关于火星殖民的科幻开头"}]
  }'
```

**响应**:
```json
{
  "id": "chatcmpl-gemini-reverse",
  "object": "chat.completion",
  "model": "gemini-3-flash-preview",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "公元2087年，当第一艘殖民船..."},
    "finish_reason": "stop"
  }]
}
```

### POST /v1/generate (简化格式)

简化版文本生成接口。

```bash
curl -X POST https://google-api.aihang365.com/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "1+1=?", "model": "gemini-3-flash-preview"}'
```

---

## 图片生成

### POST /v1/generate-images

生成图片，**自动去除 Gemini 水印** ✨

**参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 图片描述 |
| count | int | 否 | 1 | 生成数量 |
| response_type | string | 否 | "base64" | 返回格式: "base64" 或 "url" |
| image | string | 否 | - | 参考图base64（用于图片编辑） |

**去水印说明**: 所有生成的图片都会自动通过反向Alpha混合算法去除 Gemini SynthID 水印，无需额外参数。

**示例1: 生成图片返回base64**

```bash
curl -X POST https://google-api.aihang365.com/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a beautiful sunset", "response_type": "base64"}'
```

**响应**:
```json
{
  "images": ["data:image/png;base64,iVBORw0KGgo..."],
  "model": "gemini-2.5-flash"
}
```

**示例2: 生成高质量图片返回URL**

```bash
curl -X POST https://google-api.aihang365.com/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{"prompt": "赛博朋克风格的上海街头，雨夜，霓虹灯", "response_type": "url"}'
```

**响应**:
```json
{
  "images": ["https://pub-xxx.r2.dev/gemini-images/20251226_103153_cyberpunk_c67ba5.png"],
  "model": "gemini-2.5-flash"
}
```

> 文件名格式: `{时间戳}_{关键词}_{hash}.png`，便于grep搜索

### 模型选择建议

| 场景 | 推荐模型 | 参数示例 |
|------|---------|---------|
| 快速预览 | gemini-2.5-flash-image | 默认，无需指定 |
| 高质量 | gemini-3-pro-image-preview | 添加到prompt中说明 |
| 2K高清 | gemini-3-pro-image-preview-2k | prompt加"2K resolution" |
| 4K超高清 | gemini-3-pro-image-preview-4k | prompt加"4K ultra HD" |

---

## 参考图编辑

### POST /v1/images/edit
### POST /v1/images/edits

基于参考图生成新图片，支持风格转换、背景替换、元素添加等场景。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 编辑指令 |
| image | string | 是 | 参考图base64（支持data:image前缀） |
| response_type | string | 否 | "base64"(默认) 或 "url" |

**Bash示例**:

```bash
# 准备参考图base64
IMAGE_BASE64=$(base64 -i input.png)

# 调用 API 进行图片编辑
curl -X POST https://google-api.aihang365.com/v1/images/edit \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"将背景改为蓝色天空\",
    \"image\": \"data:image/png;base64,${IMAGE_BASE64}\",
    \"response_type\": \"url\"
  }"
```

**Python示例**:

```python
import requests
import base64

# 读取参考图
with open("input.png", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

# 调用 API
response = requests.post(
    "https://google-api.aihang365.com/v1/images/edit",
    json={
        "prompt": "把猫咪变成卡通风格",
        "image": f"data:image/png;base64,{image_base64}",
        "response_type": "url"
    }
)

result = response.json()
print(f"生成的图片: {result['images'][0]}")
```

**常用编辑指令**:

| 指令 | 效果 |
|------|------|
| "将背景改为白色" | 更换背景颜色 |
| "转换为水彩画风格" | 风格转换 |
| "移除图片中的文字" | 去除水印/文字 |
| "添加一只小狗" | 添加元素 |
| "将白天改为夜晚" | 光线/时间调整 |

---

## 批量任务

### POST /v1/batch/images

批量图片生成（后台并发处理，支持断点续传）。

**参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompts | array | 是 | - | prompt列表 |
| response_type | string | 否 | "url" | "base64" 或 "url" |
| concurrency | int | 否 | 2 | 并发数（最大2） |

**示例**:

```bash
curl -X POST https://google-api.aihang365.com/v1/batch/images \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": [
      "a red sports car",
      "a blue ocean",
      "a green forest"
    ],
    "response_type": "url",
    "concurrency": 2
  }'
```

**响应**:
```json
{
  "batch_id": "batch_60bfcf0a",
  "total": 3,
  "status": "processing",
  "message": "批量任务已创建，2并发处理中"
}
```

### GET /v1/batch/{batch_id}/status

查询批量任务状态。

```bash
curl https://google-api.aihang365.com/v1/batch/batch_60bfcf0a/status
```

**响应**:
```json
{
  "batch_id": "batch_60bfcf0a",
  "total": 3,
  "completed": 2,
  "failed": 0,
  "pending": 1,
  "progress": "2/3",
  "status": "processing",
  "results": [
    {"task_id": "batch_60bfcf0a_task_0", "url": "https://..."},
    {"task_id": "batch_60bfcf0a_task_1", "url": "https://..."}
  ],
  "errors": []
}
```

---

## 健康检查

### GET /health

检查服务状态。

```bash
curl https://google-api.aihang365.com/health
```

**响应**:
```json
{
  "status": "ok",
  "version": "3.1",
  "client_ready": true,
  "watermark_removal": true,
  "rate_limiter": {
    "current_delay": 2.0,
    "requests_last_minute": 3,
    "consecutive_429s": 0,
    "rpm_limit": 60
  },
  "task_stats": {
    "pending": 0,
    "processing": 0,
    "completed": 10,
    "failed": 0,
    "total": 10
  },
  "concurrency": {
    "max": 2,
    "available": 2
  }
}
```

---

## Gemini 原生格式

### POST /gemini/v1beta/models/{model}:generateContent

Gemini 原生格式接口。

```bash
curl -X POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-3-flash-preview:generateContent \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "你好"}]
    }]
  }'
```

---

## 限制说明

| 限制项 | 值 | 说明 |
|--------|-----|------|
| 频率限制 | 60次/小时/IP | 全局限制 |
| 同模型间隔 | 5秒 | 单模型请求间隔 |
| 最大并发 | 2 | 同时处理的请求数 |
| 图片最大分辨率 | 4096x4096 | 4K超高清 |
| Cookie有效期 | 1-2个月 | 建议定期更新 |

---

## 错误码

| 状态码 | 说明 | 处理建议 |
|--------|------|---------|
| 200 | 成功 | - |
| 400 | 参数错误 | 检查 model 名称或 prompt 格式 |
| 429 | 频率限制 | 降低请求频率，等待重试 |
| 503 | Cookie未配置 | 联系管理员 |
| 500 | 服务器错误 | 重试或联系管理员 |

---

## 技术特性

### 智能重试
- 指数退避算法：2s → 4s → 8s → 16s → 32s
- 最多重试5次
- 仅重试 429/5xx 错误

### 智能速率控制
- 动态延迟调整
- 随机抖动防惊群效应
- RPM限制：60/分钟

### 断点续传
- SQLite状态持久化
- 任务中断后自动恢复
- 支持批量任务进度查询

### 自动去水印
- 反向Alpha混合算法
- 毫秒级处理速度
- 失败时优雅降级返回原图

---

**服务地址**: https://google-api.aihang365.com
**文档版本**: v3.1
**最后更新**: 2025-12-26
