# Gemini Reverse API - 第三方集成指南

本文档帮助第三方平台（如AiHubMix、ocoolAI等）接入我们的Gemini Reverse API。

---

## 📊 快速配置

### 基本信息

| 项目 | 内容 |
|------|------|
| **服务地址** | `https://google-api.aihang365.com` |
| **API密钥** | 不需要（或填写任意字符串） |
| **支持格式** | Gemini原生格式 + OpenAI兼容格式 |
| **模型数量** | 7个（3个文本 + 4个图片） |

---

## 🎯 配置方案

### 方案1: Gemini原生格式（推荐）

**适用场景**: 平台支持Gemini/Google AI格式

#### 配置参数

```yaml
API类型: Gemini / Google AI
Base URL: https://google-api.aihang365.com
端点格式: /gemini/v1beta/models/{model}:generateContent
API密钥: 不需要（可留空或填任意值）
```

#### 文本生成示例

```bash
POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-2.5-flash:generateContent

Content-Type: application/json

{
  "contents": [{
    "parts": [{"text": "解释一下量子计算"}]
  }],
  "generationConfig": {
    "temperature": 0.7,
    "maxOutputTokens": 2048
  }
}
```

#### 图片生成示例

```bash
POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-3-pro-image-preview:generateContent

Content-Type: application/json

{
  "contents": [{
    "parts": [{"text": "a beautiful sunset over the ocean, photorealistic"}]
  }],
  "generationConfig": {
    "temperature": 1.0
  }
}
```

---

### 方案2: OpenAI兼容格式

**适用场景**: 平台原生支持OpenAI，需要快速接入

#### 配置参数

```yaml
API类型: OpenAI Compatible
Base URL: https://google-api.aihang365.com/v1
API密钥: gemini-reverse-2025
```

#### 文本生成示例

```bash
POST https://google-api.aihang365.com/v1/chat/completions

Content-Type: application/json
Authorization: Bearer gemini-reverse-2025

{
  "model": "gemini-2.5-flash",
  "messages": [
    {"role": "user", "content": "解释一下量子计算"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048
}
```

#### 图片生成示例

```bash
POST https://google-api.aihang365.com/v1/images/generations

Content-Type: application/json
Authorization: Bearer gemini-reverse-2025

{
  "model": "gemini-3-pro-image-preview",
  "prompt": "a beautiful sunset over the ocean, photorealistic",
  "size": "2048x2048",
  "n": 1
}
```

---

## 📋 支持的模型列表

### 文本模型 (3个)

| 模型ID | 显示名称 | 描述 | 速度 | 推荐场景 |
|--------|---------|------|------|---------|
| `gemini-2.5-flash` | Gemini 2.5 Flash | 快速响应 | ⚡⚡⚡ | 日常对话 |
| `gemini-2.5-pro` | Gemini 2.5 Pro | 高阶推理 | ⚡⚡ | 代码/数学 |
| `gemini-3.0-pro` | Gemini 3.0 Pro | 最新Pro | ⚡⚡ | 复杂任务 |

### 图片生成模型 (4个)

| 模型ID | 显示名称 | 分辨率 | 速度 | 推荐场景 |
|--------|---------|--------|------|---------|
| `gemini-2.5-flash-image` | Gemini 2.5 Flash Image | 标准 | ⚡⚡⚡ (~30s) | 快速预览 |
| `gemini-3-pro-image-preview` | Gemini 3 Pro Image | 2048x2048 | ⚡⚡ (~60s) | 标准高质量 |
| `gemini-3-pro-image-preview-2k` | Gemini 3 Pro Image 2K | 2048x2048 | ⚡⚡ (~60s) | 日常使用 |
| `gemini-3-pro-image-preview-4k` | Gemini 3 Pro Image 4K | 4096x4096 | ⚡ (~90s) | 超高清 |

---

## 🔧 API端点列表

### 健康检查

```bash
GET  /health                  # 服务健康检查
GET  /api/info                # API信息
GET  /api/cookies/status      # Cookie状态
GET  /api/models              # 模型列表
GET  /v1/models               # OpenAI格式模型列表
```

### 文本生成

```bash
# Gemini原生格式
POST /gemini/v1beta/models/{model}:generateContent

# OpenAI兼容格式
POST /v1/chat/completions
POST /v1/generate
```

### 图片生成

```bash
# Gemini原生格式
POST /gemini/v1beta/models/{model}:generateContent

# OpenAI兼容格式
POST /v1/images/generations
POST /v1/generate-images
```

### 图片编辑

```bash
# Gemini原生格式
POST /gemini/v1beta/models/{model}:editImage

# OpenAI兼容格式
POST /v1/images/edit
POST /v1/images/edits
```

---

## 🧪 测试步骤

### 1. 健康检查

```bash
curl -s https://google-api.aihang365.com/health
# 预期: {"status":"ok","client_ready":true}
```

### 2. 列出模型

**Gemini格式**:
```bash
curl -s https://google-api.aihang365.com/api/models
```

**OpenAI格式**:
```bash
curl -s https://google-api.aihang365.com/v1/models
```

### 3. 测试文本生成

**Gemini格式**:
```bash
curl -X POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-2.5-flash:generateContent \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"你好"}]}]}'
```

**OpenAI格式**:
```bash
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"你好"}]}'
```

### 4. 测试图片生成

**Gemini格式**:
```bash
curl -X POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-3-pro-image-preview:generateContent \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"a cat"}]}]}' \
  -o test.jpg
```

**OpenAI格式**:
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-3-pro-image-preview","prompt":"a cat"}' \
  | jq -r '.data[0].url' | xargs curl -o test.jpg
```

---

## ⚠️ 限流规则

### 当前限流配置

- **全局限流**: 60次/小时/IP
- **模型级别**: 同一模型5秒间隔

### 限流响应

```json
{
  "detail": "模型 gemini-2.5-flash 调用过于频繁，请等待 4.2 秒后重试"
}
```

---

## 🔒 安全建议

### 1. 使用域名（推荐）

不要直接暴露IP，使用域名+HTTPS：

```nginx
# Caddy配置示例
gemini-api.yourdomain.com {
    reverse_proxy 82.29.54.80:8100
}
```

配置后API地址改为：
```
https://gemini-api.yourdomain.com
```

### 2. API密钥验证（可选）

虽然当前不验证密钥，但建议在反向代理层添加验证：

```nginx
@authorized {
    header Authorization "Bearer your-secret-key"
}

handle @authorized {
    reverse_proxy 82.29.54.80:8100
}
```

### 3. 访问日志

建议记录访问日志以便监控：

```bash
# 查看实时访问
ssh root@82.29.54.80 "docker logs -f google-reverse"
```

---

## 📊 监控端点

### Cookie状态检查

```bash
curl -s https://google-api.aihang365.com/api/cookies/status
```

**响应示例**:
```json
{
  "valid": true,
  "message": "Cookie有效，客户端已就绪"
}
```

### 服务健康检查

```bash
curl -s https://google-api.aihang365.com/health
```

**响应示例**:
```json
{
  "status": "ok",
  "client_ready": true
}
```

---

## 🐛 常见问题

### Q1: 为什么不需要API密钥？

我们的API基于Cookie认证，已经在服务端配置好，客户端不需要提供密钥。

### Q2: 两种格式有什么区别？

- **Gemini原生格式**: 功能完整，支持所有Gemini特性（如function calling）
- **OpenAI格式**: 为了兼容性，功能可能受限，但接入更简单

### Q3: 如何选择模型？

- **日常对话**: `gemini-2.5-flash`（最快）
- **代码/数学**: `gemini-2.5-pro`
- **复杂推理**: `gemini-3.0-pro`
- **快速图片**: `gemini-2.5-flash-image`
- **高质量图片**: `gemini-3-pro-image-preview`
- **超高清图片**: `gemini-3-pro-image-preview-4k`

### Q4: Cookie会过期吗？

会，`__Secure-1PSIDTS` 会在几小时到几天内过期。监控 `/api/cookies/status` 端点，失效时会返回：

```json
{
  "valid": false,
  "message": "Cookie无效或已过期"
}
```

需要重新更新Cookie（参考Cookie管理文档）。

### Q5: 支持流式输出吗？

支持！在请求中添加 `"stream": true`：

**OpenAI格式**:
```json
{
  "model": "gemini-2.5-flash",
  "messages": [...],
  "stream": true
}
```

**Gemini格式**:
```bash
POST /gemini/v1beta/models/gemini-2.5-flash:streamGenerateContent
```

---

## 📞 技术支持

- **服务器**: 82.29.54.80:8100
- **容器名**: google-reverse
- **镜像**: gemini-reverse-api:latest
- **Cookie管理**: 参考 `cookie-refresh/README.md`

---

**最后更新**: 2025-12-23
**API版本**: v1
**文档版本**: 1.0
