# Gemini Reverse API - External Integration Reference

**Version**: v4.2
**Base URL**: `https://google-api.aihang365.com`
**Last Updated**: 2026-01-02
**Authentication**: None required (server-side cookie authentication)

---

## Overview

This API provides access to Google Gemini models for text generation, image generation, TTS, document analysis, and UI design understanding. It is fully compatible with OpenAI API format.

### Features

- OpenAI-compatible endpoints
- Gemini native format support
- Automatic watermark removal for images
- Multi-model support (text, image, TTS, PDF, UI)
- Rate limiting with smart retry

---

## Authentication

No API key required. All requests are authenticated server-side via Google cookies.

```bash
# No Authorization header needed
curl https://google-api.aihang365.com/health
```

---

## Base URL

| Environment | URL |
|-------------|-----|
| Production | `https://google-api.aihang365.com` |
| Direct Access | `http://82.29.54.80:8100` |

---

## Common Headers

```http
Content-Type: application/json
Accept: application/json
```

---

## Rate Limits

| Limit Type | Value | Description |
|------------|-------|-------------|
| Global RPM | 60/hour/IP | Requests per hour per IP |
| Model Interval | 5 seconds | Minimum interval between same model requests |
| Max Concurrency | 2 | Simultaneous requests |

---

# API Endpoints

## 1. Health & Status

### GET /health

Check service health status.

**Request**
```http
GET /health HTTP/1.1
Host: google-api.aihang365.com
```

**Response** `200 OK`
```json
{
  "status": "ok",
  "version": "4.2",
  "client_ready": true,
  "watermark_removal": true,
  "provider_mode": false,
  "rate_limiter": {
    "current_delay": 2.0,
    "requests_last_minute": 3,
    "consecutive_429s": 0,
    "rpm_limit": 60
  },
  "concurrency": {
    "max": 2,
    "available": 2
  }
}
```

---

### GET /api/cookies/status

Check cookie authentication status.

**Response** `200 OK`
```json
{
  "valid": true,
  "last_check": "2026-01-02T10:30:00Z",
  "cookies_configured": true
}
```

---

## 2. Models

### GET /api/models

List all available models with categories.

**Response** `200 OK`
```json
{
  "models": [
    {
      "id": "gemini-2.5-flash",
      "name": "Gemini 2.5 Flash",
      "type": "text",
      "description": "Fast text generation"
    },
    {
      "id": "gemini-2.5-pro",
      "name": "Gemini 2.5 Pro",
      "type": "text",
      "description": "Advanced reasoning"
    },
    {
      "id": "gemini-3.0-pro",
      "name": "Gemini 3.0 Pro",
      "type": "text",
      "description": "Latest Pro model"
    },
    {
      "id": "gemini-2.5-flash-image",
      "name": "Flash Image",
      "type": "image",
      "description": "Fast image generation"
    },
    {
      "id": "gemini-3-pro-image-preview",
      "name": "Pro Image",
      "type": "image",
      "description": "High quality 2048x2048"
    }
  ],
  "categories": {
    "text": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.0-pro"],
    "image": ["gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-3-pro-image-preview-2k", "gemini-3-pro-image-preview-4k"],
    "tts": ["tts-1", "tts-1-hd"],
    "document": ["gemini-2.5-flash-pdf", "gemini-2.5-pro-pdf"],
    "design": ["gemini-2.5-flash-ui", "gemini-2.5-pro-ui"]
  }
}
```

---

### GET /v1/models

OpenAI-compatible model list.

**Response** `200 OK`
```json
{
  "object": "list",
  "data": [
    {"id": "gemini-2.5-flash", "object": "model", "owned_by": "google"},
    {"id": "gemini-2.5-pro", "object": "model", "owned_by": "google"},
    {"id": "gemini-3.0-pro", "object": "model", "owned_by": "google"}
  ]
}
```

---

## 3. Text Generation

### POST /v1/chat/completions

OpenAI-compatible chat completion endpoint.

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model` | string | No | `gemini-2.5-flash` | Model ID |
| `messages` | array | Yes | - | Conversation messages |
| `messages[].role` | string | Yes | - | `user`, `assistant`, or `system` |
| `messages[].content` | string | Yes | - | Message content |
| `stream` | boolean | No | `false` | Enable streaming (not recommended) |

**Request**
```http
POST /v1/chat/completions HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "model": "gemini-2.5-flash",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ]
}
```

**Response** `200 OK`
```json
{
  "id": "chatcmpl-gemini-reverse",
  "object": "chat.completion",
  "created": 1704153600,
  "model": "gemini-2.5-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

**cURL Example**
```bash
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "Explain quantum computing in simple terms"}]
  }'
```

---

### POST /v1/generate

Simplified text generation endpoint.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Text prompt |
| `model` | string | No | Model ID (default: `gemini-2.5-flash`) |

**Request**
```http
POST /v1/generate HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "prompt": "What is 2+2?",
  "model": "gemini-2.5-flash"
}
```

**Response** `200 OK`
```json
{
  "text": "2 + 2 = 4",
  "model": "gemini-2.5-flash"
}
```

---

## 4. Image Generation

### POST /v1/generate-images

Generate images with automatic watermark removal.

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Image description |
| `count` | integer | No | `1` | Number of images (1-4) |
| `response_type` | string | No | `base64` | `base64` or `url` |
| `image` | string | No | - | Reference image base64 (for editing) |

**Request**
```http
POST /v1/generate-images HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "prompt": "A cute cat wearing a space suit on Mars",
  "response_type": "url"
}
```

**Response** `200 OK`
```json
{
  "images": [
    "https://pub-xxx.r2.dev/gemini-images/20260102_103153_cat_c67ba5.png"
  ],
  "model": "gemini-2.5-flash"
}
```

**cURL Example**
```bash
curl -X POST https://google-api.aihang365.com/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{"prompt": "cyberpunk cityscape at night", "response_type": "url"}'
```

---

### POST /v1/images/generations

OpenAI-compatible image generation.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Image description |
| `n` | integer | No | Number of images |
| `size` | string | No | Image size (ignored, auto-determined) |
| `response_format` | string | No | `url` or `b64_json` |

**Request**
```http
POST /v1/images/generations HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "prompt": "A beautiful sunset over the ocean",
  "n": 1,
  "response_format": "url"
}
```

---

### POST /v1/images/edit

Edit an existing image based on a prompt.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Edit instruction |
| `image` | string | Yes | Base64 encoded image (with or without data URI prefix) |
| `response_type` | string | No | `base64` or `url` |

**Request**
```http
POST /v1/images/edit HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "prompt": "Change the background to a beach scene",
  "image": "data:image/png;base64,iVBORw0KGgo...",
  "response_type": "url"
}
```

**Response** `200 OK`
```json
{
  "images": ["https://pub-xxx.r2.dev/gemini-images/edited_xxx.png"],
  "model": "gemini-2.5-flash"
}
```

---

## 5. Text-to-Speech (TTS)

### POST /v1/audio/speech

Generate speech from text.

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `input` | string | Yes | - | Text to convert to speech |
| `model` | string | No | `tts-1` | `tts-1` or `tts-1-hd` |
| `voice` | string | No | `alloy` | Voice selection |
| `response_format` | string | No | `wav` | Audio format |

**Available Voices**: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

**Request**
```http
POST /v1/audio/speech HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "input": "Hello, this is a test of text to speech.",
  "model": "tts-1",
  "voice": "nova"
}
```

**Response** `200 OK`
```
Content-Type: audio/wav
Content-Disposition: attachment; filename="speech.wav"

[Binary WAV data]
```

**cURL Example**
```bash
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "voice": "nova"}' \
  --output speech.wav
```

---

### GET /v1/audio/voices

List available TTS voices.

**Response** `200 OK`
```json
{
  "voices": [
    {"voice_id": "alloy", "name": "Alloy", "language": "en"},
    {"voice_id": "echo", "name": "Echo", "language": "en"},
    {"voice_id": "fable", "name": "Fable", "language": "en"},
    {"voice_id": "onyx", "name": "Onyx", "language": "en"},
    {"voice_id": "nova", "name": "Nova", "language": "en"},
    {"voice_id": "shimmer", "name": "Shimmer", "language": "en"}
  ]
}
```

---

## 6. Document Analysis

### POST /v1/documents/analyze

Analyze PDF documents.

**Request** (multipart/form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF file to analyze |
| `prompt` | string | No | Analysis instruction |
| `detail_level` | string | No | `low`, `medium`, or `high` |

**cURL Example**
```bash
curl -X POST https://google-api.aihang365.com/v1/documents/analyze \
  -F "file=@document.pdf" \
  -F "prompt=Summarize the main points of this document" \
  -F "detail_level=high"
```

**Response** `200 OK`
```json
{
  "analysis": "This document discusses...",
  "pages": 5,
  "model": "gemini-2.5-flash"
}
```

---

### POST /v1/documents/extract

Extract structured data from PDF.

**Request** (multipart/form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF file |
| `extract_type` | string | No | `text`, `tables`, or `all` |

**Response** `200 OK`
```json
{
  "text": "Extracted text content...",
  "tables": [],
  "metadata": {
    "pages": 3,
    "title": "Document Title"
  }
}
```

---

## 7. UI Design Analysis

### POST /v1/design/analyze

Analyze UI design images.

**Request** (multipart/form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | UI design image (PNG/JPG) |
| `prompt` | string | No | Analysis focus |

**cURL Example**
```bash
curl -X POST https://google-api.aihang365.com/v1/design/analyze \
  -F "file=@ui_mockup.png" \
  -F "prompt=Analyze the layout and suggest improvements"
```

**Response** `200 OK`
```json
{
  "analysis": "This UI design features a clean layout with...",
  "components": ["header", "sidebar", "main content", "footer"],
  "suggestions": ["Consider adding more whitespace...", "..."],
  "model": "gemini-2.5-flash"
}
```

---

### POST /v1/design/to-code

Convert UI design to code.

**Request** (multipart/form-data)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | file | Yes | - | UI design image |
| `framework` | string | No | `react` | `react`, `vue`, `html` |
| `style_library` | string | No | `tailwind` | `tailwind`, `css`, `styled-components` |

**cURL Example**
```bash
curl -X POST https://google-api.aihang365.com/v1/design/to-code \
  -F "file=@button_design.png" \
  -F "framework=react" \
  -F "style_library=tailwind"
```

**Response** `200 OK`
```json
{
  "code": "import React from 'react';\n\nconst Button = () => {\n  return (\n    <button className=\"px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600\">\n      Click Me\n    </button>\n  );\n};\n\nexport default Button;",
  "framework": "react",
  "style_library": "tailwind"
}
```

---

## 8. Batch Operations

### POST /v1/batch/images

Create a batch image generation job.

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompts` | array | Yes | - | Array of image prompts |
| `response_type` | string | No | `url` | `base64` or `url` |
| `concurrency` | integer | No | `2` | Parallel jobs (max 2) |

**Request**
```http
POST /v1/batch/images HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "prompts": [
    "A red sports car",
    "A blue ocean",
    "A green forest"
  ],
  "response_type": "url",
  "concurrency": 2
}
```

**Response** `202 Accepted`
```json
{
  "batch_id": "batch_60bfcf0a",
  "total": 3,
  "status": "processing",
  "message": "Batch job created, processing with 2 concurrent workers"
}
```

---

### GET /v1/batch/{batch_id}/status

Get batch job status.

**Request**
```http
GET /v1/batch/batch_60bfcf0a/status HTTP/1.1
Host: google-api.aihang365.com
```

**Response** `200 OK`
```json
{
  "batch_id": "batch_60bfcf0a",
  "total": 3,
  "completed": 2,
  "failed": 0,
  "pending": 1,
  "progress": "66.7%",
  "status": "processing",
  "results": [
    {"task_id": "batch_60bfcf0a_task_0", "url": "https://..."},
    {"task_id": "batch_60bfcf0a_task_1", "url": "https://..."}
  ],
  "errors": []
}
```

---

## 9. Gemini Native Format

### POST /gemini/v1beta/models/{model}:generateContent

Gemini native API format for direct integration.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | string | Model ID (e.g., `gemini-2.5-flash`) |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `contents` | array | Yes | Conversation contents |
| `contents[].role` | string | Yes | `user` or `model` |
| `contents[].parts` | array | Yes | Content parts |
| `contents[].parts[].text` | string | Yes | Text content |

**Request**
```http
POST /gemini/v1beta/models/gemini-2.5-flash:generateContent HTTP/1.1
Host: google-api.aihang365.com
Content-Type: application/json

{
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "Hello, Gemini!"}]
    }
  ]
}
```

**Response** `200 OK`
```json
{
  "candidates": [
    {
      "content": {
        "role": "model",
        "parts": [{"text": "Hello! How can I help you today?"}]
      },
      "finishReason": "STOP"
    }
  ]
}
```

---

### GET /gemini/v1beta/models

List models in Gemini native format.

**Response** `200 OK`
```json
{
  "models": [
    {
      "name": "models/gemini-2.5-flash",
      "displayName": "Gemini 2.5 Flash",
      "description": "Fast and efficient model"
    }
  ]
}
```

---

## Error Responses

### Error Format

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable error message",
    "type": "error_type"
  }
}
```

### HTTP Status Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| `200` | Success | Request completed successfully |
| `400` | Bad Request | Invalid parameters, missing required fields |
| `401` | Unauthorized | Invalid or expired cookies |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side error |
| `503` | Service Unavailable | Cookies not configured or expired |

### Error Examples

**400 Bad Request**
```json
{
  "detail": "Client error: Unknown model name: invalid-model. Available models: gemini-2.5-flash, gemini-2.5-pro, gemini-3.0-pro"
}
```

**429 Rate Limited**
```json
{
  "detail": "Model gemini-2.5-flash rate limited, please wait 4.2 seconds"
}
```

**503 Cookie Error**
```json
{
  "detail": "Cookie authentication failed. Please update cookies."
}
```

---

## SDK Integration Examples

### Python

```python
import requests

BASE_URL = "https://google-api.aihang365.com"

def chat(message: str, model: str = "gemini-2.5-flash") -> str:
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}]
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def generate_image(prompt: str) -> str:
    response = requests.post(
        f"{BASE_URL}/v1/generate-images",
        json={"prompt": prompt, "response_type": "url"}
    )
    response.raise_for_status()
    return response.json()["images"][0]

# Usage
print(chat("What is the capital of France?"))
print(generate_image("A beautiful mountain landscape"))
```

### JavaScript/Node.js

```javascript
const BASE_URL = "https://google-api.aihang365.com";

async function chat(message, model = "gemini-2.5-flash") {
  const response = await fetch(`${BASE_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: message }]
    })
  });
  const data = await response.json();
  return data.choices[0].message.content;
}

async function generateImage(prompt) {
  const response = await fetch(`${BASE_URL}/v1/generate-images`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, response_type: "url" })
  });
  const data = await response.json();
  return data.images[0];
}

// Usage
chat("Hello!").then(console.log);
generateImage("A cute robot").then(console.log);
```

### cURL

```bash
# Text generation
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"Hello"}]}'

# Image generation
curl -X POST https://google-api.aihang365.com/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A sunset","response_type":"url"}'

# TTS
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello world","voice":"nova"}' \
  --output speech.wav
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 4.2 | 2026-01-02 | Added TTS, PDF analysis, UI design endpoints |
| 4.1 | 2025-12-29 | Cookie auto-refresh, Provider mode |
| 4.0 | 2025-12-28 | Major refactor, watermark removal |
| 3.1 | 2025-12-26 | Batch operations, rate limiting |

---

## Support

- **Documentation**: This file
- **Health Check**: `GET /health`
- **Model List**: `GET /api/models`

---

**Base URL**: `https://google-api.aihang365.com`
**Version**: v4.2
**Last Updated**: 2026-01-02
