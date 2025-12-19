# Gemini Reverse API 文档

## 📌 服务信息

- **基础URL**: `http://82.29.54.80:8100`
- **域名**: `http://google-api.aihang365.com:8100`
- **协议**: HTTP
- **版本**: v1.1
- **认证**: 无需 API Key（基于服务端 Cookie）

---

## 🚀 快速开始

### 最简单的调用（推荐）

```bash
curl -X POST http://82.29.54.80:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

---

## 📡 API 端点

### 1. 健康检查

检查服务是否正常运行。

**端点**: `GET /health`

**请求示例**:
```bash
curl http://82.29.54.80:8100/health
```

**响应**:
```json
{
  "status": "ok",
  "client_ready": true
}
```

> `client_ready` 表示Cookie是否已配置且客户端已初始化

---

### 2. Web配置界面

**端点**: `GET /`

返回Web配置界面（HTML页面），用于配置Cookie和测试API。

---

### 3. API服务信息

获取 API 服务信息和可用端点。

**端点**: `GET /api/info`

**请求示例**:
```bash
curl http://82.29.54.80:8100/api/info
```

**响应**:
```json
{
  "service": "Gemini Reverse API",
  "version": "1.0",
  "endpoints": {
    "openai": "/v1/chat/completions",
    "gemini": "/gemini/v1beta/models/{model}:generateContent",
    "simple": "/v1/generate",
    "cookie_config": "/api/cookies"
  }
}
```

---

### 4. Cookie管理

#### 获取Cookie状态

**端点**: `GET /api/cookies/status`

**响应**:
```json
{
  "valid": true,
  "message": "Cookie有效，客户端已就绪"
}
```

#### 配置Cookie

**端点**: `POST /api/cookies`

**请求**:
```json
{
  "cookies": {
    "__Secure-1PSID": "xxx",
    "__Secure-1PSIDCC": "xxx",
    "__Secure-1PSIDTS": "xxx"
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "Cookie保存成功，客户端已重新初始化"
}
```

---

### 5. 获取模型列表

**端点**: `GET /api/models`

**响应**:
```json
{
  "models": [
    {"id": "gemini-2.5-flash", "name": "快速", "description": "快速回答，适合日常使用"},
    {"id": "gemini-2.5-pro", "name": "Pro", "description": "擅长处理高阶数学和代码问题"},
    {"id": "gemini-3.0-pro", "name": "Pro 3.0", "description": "最新Pro模型，更强的推理能力"}
  ],
  "default": "gemini-2.5-flash"
}
```

---

## 🔄 三种调用格式

### 格式 1: OpenAI 兼容格式（推荐）⭐

适合从 OpenAI API 迁移的用户，无需修改代码。

**端点**: `POST /v1/chat/completions`

**请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | 否 | `gemini-2.5-flash` | 模型名称 |
| `messages` | array | 是 | - | 消息数组 |
| `messages[].role` | string | 是 | - | 角色：`user` 或 `assistant` |
| `messages[].content` | string | 是 | - | 消息内容 |

**请求示例**:
```bash
curl -X POST http://82.29.54.80:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [
      {"role": "user", "content": "解释一下量子计算"}
    ]
  }'
```

**响应格式**:
```json
{
  "id": "chatcmpl-1734567890",
  "object": "chat.completion",
  "created": 1734567890,
  "model": "gemini-2.5-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "量子计算是一种利用量子力学原理..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}
```

**Python 示例**:
```python
import requests

response = requests.post(
    "http://82.29.54.80:8100/v1/chat/completions",
    json={
        "model": "gemini-2.5-flash",
        "messages": [
            {"role": "user", "content": "你好"}
        ]
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

**Node.js 示例**:
```javascript
const axios = require('axios');

async function chat(message) {
  const response = await axios.post(
    'http://82.29.54.80:8100/v1/chat/completions',
    {
      model: 'gemini-2.5-flash',
      messages: [
        { role: 'user', content: message }
      ]
    }
  );

  return response.data.choices[0].message.content;
}

chat('你好').then(console.log);
```

---

### 格式 2: Gemini 原生格式

Google 官方 API 兼容格式，提供完整的 Token 统计。

**端点**: `POST /gemini/v1beta/models/{model}:generateContent`

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型名称，如 `gemini-3-pro-preview` |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `contents` | array | 是 | 内容数组 |
| `contents[].role` | string | 是 | 角色：`user` 或 `model` |
| `contents[].parts` | array | 是 | 内容部分数组 |
| `contents[].parts[].text` | string | 是 | 文本内容 |
| `generationConfig` | object | 否 | 生成配置（可选） |
| `generationConfig.temperature` | float | 否 | 温度参数（0.0-1.0） |
| `generationConfig.maxOutputTokens` | int | 否 | 最大输出 token 数 |

**请求示例**:
```bash
curl -X POST http://82.29.54.80:8100/gemini/v1beta/models/gemini-3-pro-preview:generateContent \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      {
        "role": "user",
        "parts": [{"text": "解释一下机器学习"}]
      }
    ],
    "generationConfig": {
      "temperature": 0.7,
      "maxOutputTokens": 1000
    }
  }'
```

**响应格式**:
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "机器学习是人工智能的一个分支..."
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 8,
    "candidatesTokenCount": 245,
    "totalTokenCount": 253
  },
  "modelVersion": "gemini-3-pro-preview"
}
```

**Python 示例**:
```python
import requests

response = requests.post(
    "http://82.29.54.80:8100/gemini/v1beta/models/gemini-3-pro-preview:generateContent",
    json={
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "你好"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500
        }
    }
)

result = response.json()
text = result["candidates"][0]["content"]["parts"][0]["text"]
tokens = result["usageMetadata"]["totalTokenCount"]
print(f"回复: {text}\n使用 Token: {tokens}")
```

---

### 格式 3: 简化格式

最简单的调用方式，适合快速测试。

**端点**: `POST /v1/generate`

**请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | 是 | - | 提示词 |
| `model` | string | 否 | `gemini-2.5-flash` | 模型名称 |

**请求示例**:
```bash
curl -X POST http://82.29.54.80:8100/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "写一首关于春天的诗",
    "model": "gemini-2.5-flash"
  }'
```

**响应格式**:
```json
{
  "text": "春风拂面暖人心，\n万物复苏展新颜...",
  "model": "gemini-2.5-flash"
}
```

**Python 示例**:
```python
import requests

response = requests.post(
    "http://82.29.54.80:8100/v1/generate",
    json={
        "prompt": "你好",
        "model": "gemini-2.5-flash"
    }
)

print(response.json()["text"])
```

---

## 🖼️ 图片生成接口

### 格式 1: OpenAI 兼容格式

**端点**: `POST /v1/images/generations`

**请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | 是 | - | 图片描述 |
| `model` | string | 否 | `gemini-2.5-flash` | 图片模型 |
| `n` | int | 否 | 1 | 生成数量 |
| `response_format` | string | 否 | `b64_json` | 返回格式 |

**请求示例**:
```bash
curl -X POST http://82.29.54.80:8100/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的橘猫在阳光下睡觉",
    "model": "gemini-3-pro-image-preview",
    "n": 1
  }'
```

**响应格式**:
```json
{
  "created": 1734567890,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}
```

**Python 示例**:
```python
import requests
import base64

response = requests.post(
    "http://82.29.54.80:8100/v1/images/generations",
    json={
        "prompt": "一只可爱的橘猫在阳光下睡觉",
        "model": "gemini-3-pro-image-preview"
    }
)

result = response.json()
image_data = base64.b64decode(result["data"][0]["b64_json"])

# 保存图片
with open("cat.png", "wb") as f:
    f.write(image_data)
```

---

### 格式 2: Gemini 原生格式（图片生成）

**端点**: `POST /gemini/v1beta/models/{model}:generateContent`

图片生成使用与文本相同的接口，模型会根据提示词自动生成图片。

**请求示例**:
```bash
curl -X POST http://82.29.54.80:8100/gemini/v1beta/models/gemini-3-pro-image-preview:generateContent \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      {
        "role": "user",
        "parts": [{"text": "Create an image: 一只可爱的橘猫在阳光下睡觉"}]
      }
    ]
  }'
```

**响应格式**:
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {"text": "Here is the image..."},
          {
            "inlineData": {
              "mimeType": "image/png",
              "data": "iVBORw0KGgoAAAANSUhEUgAA..."
            }
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP"
    }
  ]
}
```

---

## 🎤 语音生成接口（TTS - Text-to-Speech）

> **重要提示**: 语音功能需要使用 Google AI 官方 API Key（非 Cookie 方式）

### Python SDK 调用（推荐）

**安装依赖**:
```bash
pip install google-genai
```

**基础示例**:
```python
from google import genai

# 初始化客户端
client = genai.Client(api_key='YOUR_API_KEY')

# 文本转语音
response = client.models.generate_content(
    model='gemini-2.5-flash-preview-tts',
    contents='Hello, this is a text-to-speech test. 你好，这是语音生成测试。',
    config={'response_modalities': ['AUDIO']}
)

# 提取并保存音频
audio_data = response.candidates[0].content.parts[0].inline_data.data
with open('output.wav', 'wb') as f:
    f.write(audio_data)
```

**完整示例（带错误处理）**:
```python
from google import genai

def text_to_speech(api_key: str, text: str, output_file: str):
    """
    Gemini TTS 语音生成

    Args:
        api_key: Google AI API Key
        text: 要转换为语音的文本（建议3000-5000字符以内）
        output_file: 输出音频文件路径

    Returns:
        音频时长（秒）
    """
    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=text,
            config={'response_modalities': ['AUDIO']}
        )

        # 提取音频数据
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        mime_type = response.candidates[0].content.parts[0].inline_data.mime_type

        # 保存音频文件
        with open(output_file, 'wb') as f:
            f.write(audio_data)

        # 计算时长（PCM 24kHz, 16bit, mono）
        sample_rate = 24000
        bytes_per_sample = 2
        duration = len(audio_data) / (sample_rate * bytes_per_sample)

        print(f"✅ 音频已保存: {output_file}")
        print(f"📊 大小: {len(audio_data):,} bytes ({len(audio_data)/1024:.1f} KB)")
        print(f"⏱️  时长: {duration:.2f} 秒 ({duration/60:.2f} 分钟)")
        print(f"🎼 格式: {mime_type}")

        return duration

    except Exception as e:
        print(f"❌ 错误: {e}")
        raise

# 使用示例
text_to_speech(
    api_key='YOUR_API_KEY',
    text='你好，世界！这是一个语音生成测试。',
    output_file='output.wav'
)
```

**分段处理长文本**:
```python
def split_text_for_tts(text: str, max_chars: int = 3000):
    """
    将长文本分段，避免超出时长限制

    Args:
        text: 原始文本
        max_chars: 每段最大字符数（推荐3000）

    Returns:
        分段后的文本列表
    """
    sentences = text.split('.')
    chunks = []
    current = ''

    for sentence in sentences:
        if len(current) + len(sentence) < max_chars:
            current += sentence + '.'
        else:
            if current:
                chunks.append(current)
            current = sentence + '.'

    if current:
        chunks.append(current)

    return chunks

# 使用示例
long_text = "这是一段很长的文本..." * 1000
chunks = split_text_for_tts(long_text, max_chars=3000)

for i, chunk in enumerate(chunks):
    text_to_speech(
        api_key='YOUR_API_KEY',
        text=chunk,
        output_file=f'output_part_{i+1}.wav'
    )
```

### 配额与限制

| 项目 | 免费套餐 | 付费套餐 |
|------|---------|---------|
| **每日请求数** | 50次 | 无限制（按用量计费） |
| **单次时长** | 5分钟（推荐） | 最大11分钟 |
| **每日总时长** | ~250分钟（4.2小时） | 无限制 |
| **音频格式** | PCM 24kHz 16bit | 同左 |
| **语速** | 15-20字符/秒 | 同左 |

### 最佳实践

1. **控制文本长度**: 单次请求控制在 3000-5000 字符以内（约3-5分钟音频）
2. **长文本分段**: 超过5000字符建议分段处理
3. **错误处理**: 添加重试机制，处理网络超时
4. **音频格式**: 输出为 PCM 格式，可使用 ffmpeg 转换为 MP3：
   ```bash
   ffmpeg -f s16le -ar 24000 -ac 1 -i input.wav output.mp3
   ```

---

## 🎯 支持的模型

### 文本模型

| 模型名称 | 说明 | 推荐场景 | 速度 | 质量 |
|---------|------|---------|------|------|
| **gemini-3-flash-preview** | 3.0 Flash 预览版 ⭐ 推荐 | 最新快速模型 | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| **gemini-2.5-flash** | 快速模型 | 日常对话、快速生成 | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ |
| **gemini-2.5-pro** | Pro模型 | 高阶数学、代码问题 | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| **gemini-3.0-pro** | 3.0 Pro | 深度推理、复杂任务 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| **gemini-3-pro-preview** | Pro预览版（别名） | 同上 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |

### 图片模型

| 模型名称 | 说明 | 推荐场景 | 速度 | 质量 |
|---------|------|---------|------|------|
| **gemini-2.5-flash-image** | 快速图片生成 | 日常图片生成 | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ |
| **gemini-3-pro-image-preview** | Pro图片生成 | 高质量图片 | ⚡⚡ | ⭐⭐⭐⭐⭐ |

### 语音模型（TTS - Text-to-Speech）

> **注意**: 语音功能需要使用 Google AI 官方 API Key，不支持 Cookie 方式

| 模型名称 | 说明 | 音频格式 | 单次时长限制 | 配额 |
|---------|------|---------|------------|------|
| **gemini-2.5-flash-preview-tts** | Flash TTS（推荐）⭐ | PCM 24kHz | 5-7分钟 | 免费50次/天 |
| **gemini-2.5-pro-preview-tts** | Pro TTS | PCM 24kHz | 5-7分钟 | 免费50次/天 |

**TTS 时长限制详解**:

| 时长范围 | 稳定性 | 建议 | 字符数参考 |
|---------|--------|------|-----------|
| **0-5分钟** | ✅ 非常稳定 | **推荐使用** | ~3,000-5,000 字符 |
| **5-7分钟** | ⚠️ 可能截断 | 谨慎使用 | ~5,000-8,000 字符 |
| **7-11分钟** | ❌ 经常截断 | 不推荐 | > 8,000 字符 |
| **>11分钟** | ❌ 不支持 | 必须分段 | - |

**语速参考**: 中英文混合约 15-20 字符/秒

**免费配额使用时长**:
- 50次 × 5分钟 = **250分钟（4.2小时）/天**
- 50次 × 3分钟 = **150分钟（2.5小时）/天**

**付费价格参考**（仅供参考）:
- 每秒音频 = 25 tokens
- 1小时音频 ≈ $0.135（约1元人民币）

**模型选择建议**:
- 日常对话：使用 `gemini-3-flash-preview`（最新、速度快、质量高）⭐ 推荐
- 快速生成：使用 `gemini-2.5-flash`（稳定、不限配额）
- 复杂推理：使用 `gemini-2.5-pro` 或 `gemini-3.0-pro`
- 图片生成：使用 `gemini-3-pro-image-preview`（质量高）
- 语音生成：使用 `gemini-2.5-flash-preview-tts`（稳定、免费50次/天）⭐ 推荐

---

## 📊 格式对比

| 特性 | OpenAI 格式 | Gemini 格式 | 简化格式 |
|------|------------|------------|---------|
| **兼容性** | OpenAI 工具直接用 | Google 官方格式 | 最简单 |
| **Token 统计** | ❌ | ✅ | ❌ |
| **多轮对话** | ✅ 支持 | ✅ 支持 | ❌ |
| **配置参数** | ❌ | ✅ 完整 | ❌ |
| **推荐场景** | 替换 OpenAI API | 需要完整元数据 | 快速测试 |

---

## 🔧 集成示例

### 替换 OpenAI SDK

```python
# 原来的 OpenAI 代码
# from openai import OpenAI
# client = OpenAI(api_key="sk-xxx")

# 改为直接 HTTP 调用
import requests

def chat(messages):
    response = requests.post(
        "http://82.29.54.80:8100/v1/chat/completions",
        json={
            "model": "gemini-2.5-flash",
            "messages": messages
        }
    )
    return response.json()["choices"][0]["message"]["content"]

# 使用方式完全相同
result = chat([
    {"role": "user", "content": "你好"}
])
print(result)
```

---

### 集成到 LangChain

```python
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# 使用自定义端点
llm = ChatOpenAI(
    model_name="gemini-2.5-flash",
    openai_api_base="http://82.29.54.80:8100/v1",
    openai_api_key="dummy"  # 不需要真实 key
)

# 正常使用
response = llm([HumanMessage(content="你好")])
print(response.content)
```

---

## ⚠️ 限制与配额

### 服务限制

| 限制项 | 说明 |
|--------|------|
| **依赖配额** | 使用 Google 账号的 Gemini 应用配额 |
| **Cookie 有效期** | 约 1-2 周，过期需更新 |
| **流式输出** | ❌ 暂不支持（开发中） |
| **并发限制** | 受 Google 官方限制 |
| **上下文窗口** | 取决于账号订阅级别 |

### Google AI 方案配额

| 方案 | Flash 模型 | Pro 模型 | 上下文窗口 |
|------|-----------|----------|-----------|
| **免费版** | 常规使用 | 限额不稳定 | 3.2 万 token |
| **Google AI Pro** | 常规使用 | 100 条/天 | 100 万 token |
| **Google AI Ultra** | 常规使用 | 500 条/天 | 100 万 token |

**建议**:
- 日常使用：`gemini-2.5-flash`（不受限）
- 复杂任务：`gemini-3-pro-preview`（注意配额）

---

## ❌ 错误处理

### 标准错误格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误

| HTTP 状态码 | 错误原因 | 解决方法 |
|------------|---------|---------|
| **400** | 请求参数错误 | 检查 `messages` 或 `contents` 是否为空 |
| **500** | 服务内部错误 | 检查服务状态或联系管理员 |
| **503** | 服务不可用 | Cookie 可能已过期，需要更新 |

### 错误处理示例

```python
import requests

try:
    response = requests.post(
        "http://82.29.54.80:8100/v1/chat/completions",
        json={
            "model": "gemini-2.5-flash",
            "messages": [{"role": "user", "content": "你好"}]
        }
    )
    response.raise_for_status()
    result = response.json()
    print(result["choices"][0]["message"]["content"])

except requests.exceptions.HTTPError as e:
    print(f"HTTP 错误: {e}")
    print(f"详情: {e.response.json()}")
except Exception as e:
    print(f"其他错误: {e}")
```

---

## 🚀 性能优化建议

### 1. 模型选择策略

```
推荐工作流：
1. 默认使用 Flash（快速、不限配额）
2. 需要深度推理时切换 Pro
3. 批量任务优先用 Flash
```

### 2. 并发控制

```python
import asyncio
import aiohttp

async def chat_async(session, message):
    async with session.post(
        "http://82.29.54.80:8100/v1/chat/completions",
        json={
            "model": "gemini-2.5-flash",
            "messages": [{"role": "user", "content": message}]
        }
    ) as response:
        return await response.json()

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [
            chat_async(session, f"问题 {i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        return results

# 运行
results = asyncio.run(main())
```

### 3. 缓存策略

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def chat_cached(prompt):
    response = requests.post(
        "http://82.29.54.80:8100/v1/chat/completions",
        json={
            "model": "gemini-2.5-flash",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    return response.json()["choices"][0]["message"]["content"]

# 相同问题会直接返回缓存
result1 = chat_cached("什么是AI？")
result2 = chat_cached("什么是AI？")  # 使用缓存，不调用 API
```

---

## 📞 技术支持

- **服务器**: 美国服务器 (82.29.54.80)
- **端口**: 8000
- **状态**: ✅ 运行中
- **维护者**: Mason
- **部署时间**: 2025-12-17

---

## 📋 更新日志

### v1.1 (2025-12-18)
- ✅ 添加 OpenAI 图片生成接口 `/v1/images/generations`
- ✅ 添加图片模型 `gemini-2.5-flash-image` 和 `gemini-3-pro-image-preview`
- ✅ 支持多轮对话历史
- ✅ 配置域名 `google-api.aihang365.com`
- ✅ 端口改为 8100

### v1.0 (2025-12-17)
- ✅ 支持 OpenAI 兼容格式
- ✅ 支持 Gemini 原生格式
- ✅ 支持简化格式
- ✅ 支持多种模型切换
- ✅ 完整错误处理

---

## 🔗 相关链接

- **服务端点**: http://82.29.54.80:8100
- **域名访问**: http://google-api.aihang365.com:8100
- **健康检查**: http://82.29.54.80:8100/health
- **Web配置界面**: http://82.29.54.80:8100
- **API 文档**: http://82.29.54.80:8100/docs (FastAPI 自动生成)

---

## 🔌 new-api 接入配置

在 new-api 中添加自定义渠道：

| 配置项 | 值 |
|--------|-----|
| 类型 | OpenAI |
| 名称 | Gemini-Reverse |
| Base URL | `http://82.29.54.80:8100` |
| 密钥 | 任意值（如 `sk-gemini-local`） |
| 文本模型 | `gemini-2.5-flash,gemini-2.5-pro,gemini-3.0-pro,gemini-3-pro-preview` |
| 图片模型 | `gemini-2.5-flash-image,gemini-3-pro-image-preview` |

---

**最后更新**: 2025-12-18
