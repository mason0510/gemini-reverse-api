# Gemini 图片编辑 API 文档

## 📌 概述

本API提供基于Gemini的图片编辑功能，支持三种调用格式：

| 格式 | 端点 | 适用场景 |
|------|------|---------|
| **自定义格式** | `/v1/images/edit` | 直接调用 |
| **OpenAI兼容** | `/v1/images/edits` | 兼容OpenAI客户端、New API |
| **Gemini原生** | `/gemini/v1beta/models/{model}:editImage` | 兼容Google AI SDK |

---

## 🔑 认证

目前API不需要认证（基于Cookie的内部认证）。

---

## 📡 API端点详解

### 1. 自定义格式 / OpenAI兼容格式

**端点**:
- `POST /v1/images/edit`
- `POST /v1/images/edits` (别名，完全相同)

**请求体**:
```json
{
  "prompt": "编辑提示词",
  "image": "data:image/png;base64,iVBORw0KG...", // 或纯base64
  "mask": "data:image/png;base64,iVBORw0KG...",  // 可选
  "model": "gemini-3-pro-image-preview",
  "n": 1,
  "size": "1024x1024",
  "response_format": "b64_json"
}
```

**参数说明**:
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 编辑提示词，描述期望的修改 |
| `image` | string | ✅ | - | 参考图片的base64编码 |
| `mask` | string | ❌ | null | 蒙版图片的base64编码 |
| `model` | string | ❌ | `gemini-3-pro-image-preview` | 使用的模型 |
| `n` | int | ❌ | 1 | 生成数量（目前固定为1） |
| `size` | string | ❌ | `1024x1024` | 图片尺寸 |
| `response_format` | string | ❌ | `b64_json` | 响应格式 |

**响应体**:
```json
{
  "created": 1766139860,
  "data": [
    {
      "url": "data:image/png;base64,iVBORw0KG..."
    }
  ]
}
```

**示例**:
```bash
curl -X POST https://google-api.aihang365.com/v1/images/edits \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "把背景改成蓝天白云",
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUh..."
  }'
```

---

### 2. Gemini原生格式

**端点**: `POST /gemini/v1beta/models/{model}:editImage`

**路径参数**:
- `{model}`: 模型名称，如 `gemini-3-pro-image-preview`

**请求体**:
```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "编辑提示词"
        },
        {
          "inlineData": {
            "mimeType": "image/png",
            "data": "iVBORw0KGgoAAAANSUh..."
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.7
  }
}
```

**响应体**:
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "inlineData": {
              "mimeType": "image/png",
              "data": "iVBORw0KGgoAAAANSUh..."
            }
          }
        ]
      }
    }
  ]
}
```

**示例**:
```bash
curl -X POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-3-pro-image-preview:editImage \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [
        {"text": "把猫的颜色改成蓝色"},
        {"inlineData": {"mimeType": "image/png", "data": "..."}}
      ]
    }]
  }'
```

---

## 🎯 使用场景

### 场景1: 在New API中集成

1. **登录New API管理后台**: https://nexusai.satoshitech.xyz
2. **添加渠道**:
   - 渠道类型: `自定义渠道 (Custom)`
   - Base URL: `https://google-api.aihang365.com`
   - 模型映射: `dall-e-3 → gemini-3-pro-image-preview`
   - 其他设置: `{"force_format": true}`

3. **调用**:
```bash
curl -X POST https://nexusai.satoshitech.xyz/v1/images/edits \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "编辑提示词",
    "image": "data:image/png;base64,...",
    "model": "dall-e-3"
  }'
```

### 场景2: 直接调用

```python
import requests
import base64

# 读取图片
with open("image.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

# 调用API
response = requests.post(
    "https://google-api.aihang365.com/v1/images/edits",
    json={
        "prompt": "将背景改为海滩",
        "image": f"data:image/png;base64,{image_data}",
        "model": "gemini-3-pro-image-preview"
    }
)

# 保存结果
result = response.json()
edited_image_data = result["data"][0]["url"].split(",")[1]
with open("edited.png", "wb") as f:
    f.write(base64.b64decode(edited_image_data))
```

### 场景3: 使用Google AI SDK格式

```javascript
const fetch = require('node-fetch');

const response = await fetch(
  'https://google-api.aihang365.com/gemini/v1beta/models/gemini-3-pro-image-preview:editImage',
  {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      contents: [{
        parts: [
          {text: '把猫改成狗'},
          {inlineData: {mimeType: 'image/png', data: imageBase64}}
        ]
      }]
    })
  }
);

const data = await response.json();
const editedImage = data.candidates[0].content.parts[0].inlineData.data;
```

---

## ⚙️ 支持的模型

| 模型名称 | 说明 | 推荐场景 |
|---------|------|---------|
| `gemini-3-pro-image-preview` | Imagen 3（默认） | 高质量图片编辑 |
| `gemini-2.5-flash-image` | Imagen 3 Fast | 快速生成 |

---

## 🔒 反检测机制

API内置以下反检测措施：
- **频率限制**: 60次/小时/IP
- **随机延迟**: 1-3秒随机延迟
- **User-Agent轮换**: 模拟真实浏览器

---

## 📊 错误码

| HTTP状态码 | 说明 | 解决方案 |
|-----------|------|---------|
| `400` | 请求参数错误 | 检查请求体格式和必需字段 |
| `422` | 字段验证失败 | 确认字段类型和格式正确 |
| `429` | 请求过于频繁 | 等待后重试，最多60次/小时 |
| `500` | 服务器内部错误 | 检查Cookie是否有效 |
| `503` | Gemini客户端未初始化 | 联系管理员更新Cookie |

---

## 🔔 Bark通知

当Cookie过期导致服务不可用时，系统会自动发送Bark通知到管理员iPhone。

配置详见: [BARK_NOTIFICATION.md](./BARK_NOTIFICATION.md)

---

## 🛠️ 技术实现

- **框架**: FastAPI
- **Cookie管理**: gemini-webapi
- **图片处理**: PIL, base64
- **反检测**: Rate limiting + Random delays + User-Agent rotation

---

## 📝 更新日志

### v1.0.0 (2025-12-19)
- ✅ 实现 `/v1/images/edit` 自定义格式
- ✅ 实现 `/v1/images/edits` OpenAI兼容格式
- ✅ 实现 `/gemini/v1beta/models/{model}:editImage` Gemini原生格式
- ✅ 支持base64图片输入
- ✅ 支持蒙版图片（mask）
- ✅ 添加Bark通知功能
- ✅ 添加反检测机制

---

**服务器**: 82.29.54.80:8100
**维护者**: Mason
**最后更新**: 2025-12-19
