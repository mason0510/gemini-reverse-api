# Provider 多平台 API Key 支持

**功能**: 为所有接口添加 `provider` 参数，支持多个 Google AI API Key 平台切换

**更新时间**: 2025-12-20

---

## 📋 功能概述

为了解决单个 API Key 配额限制问题，我们为所有接口添加了 `provider` 参数支持，可以在多个 Google AI API Key 之间切换。

### 支持的 Provider

| Provider 名称 | 环境变量 | 说明 |
|--------------|---------|------|
| `default` | `GOOGLE_AI_API_KEY` | 主 API Key（默认） |
| `backup` | `GOOGLE_AI_API_KEY_BACKUP` | 备用 API Key |
| `platform2` | `GOOGLE_AI_API_KEY_PLATFORM2` | 平台2 API Key |
| `platform3` | `GOOGLE_AI_API_KEY_PLATFORM3` | 平台3 API Key |

---

## ⚙️ 配置方法

### 1. 编辑 `.env` 文件

```bash
# Google AI API Keys (多平台支持)
GOOGLE_AI_API_KEY=AIzaSy...  # 主 API Key
GOOGLE_AI_API_KEY_BACKUP=AIzaSy...  # 备用 API Key
GOOGLE_AI_API_KEY_PLATFORM2=AIzaSy...  # 平台2 API Key
GOOGLE_AI_API_KEY_PLATFORM3=AIzaSy...  # 平台3 API Key
```

### 2. 重新部署

```bash
./update-cookies.sh
```

---

## 🔌 API 使用

### 1. 查询可用的 Provider

**请求**:
```bash
GET https://google-api.aihang365.com/api/providers
```

**响应**:
```json
{
  "providers": [
    {
      "name": "default",
      "configured": true,
      "description": "主 API Key"
    },
    {
      "name": "backup",
      "configured": true,
      "description": "备用 API Key"
    },
    {
      "name": "platform2",
      "configured": false,
      "description": "平台2 API Key"
    },
    {
      "name": "platform3",
      "configured": false,
      "description": "平台3 API Key"
    }
  ],
  "default_provider": "default"
}
```

---

### 2. TTS 接口使用 Provider

**使用默认 Provider**:
```bash
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "这是一个测试语音"
  }' \
  --output speech.wav
```

**使用备用 Provider**:
```bash
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "这是一个测试语音",
    "provider": "backup"
  }' \
  --output speech.wav
```

**使用 Platform2**:
```bash
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "高质量语音测试",
    "provider": "platform2"
  }' \
  --output speech.wav
```

---

## 📊 使用场景

### 场景1: 配额耗尽自动切换

```python
import requests

def generate_speech_with_fallback(text, providers=["default", "backup", "platform2"]):
    """尝试多个 provider，直到成功"""
    for provider in providers:
        try:
            response = requests.post(
                "https://google-api.aihang365.com/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": text,
                    "provider": provider
                },
                timeout=30
            )

            if response.status_code == 200:
                print(f"✅ 使用 provider: {provider}")
                return response.content
            else:
                print(f"❌ {provider} 失败: {response.text}")

        except Exception as e:
            print(f"❌ {provider} 异常: {e}")

    raise Exception("所有 provider 都失败")

# 使用
audio = generate_speech_with_fallback("测试语音")
with open("output.wav", "wb") as f:
    f.write(audio)
```

---

### 场景2: 负载均衡

```python
import random

def get_random_provider():
    """随机选择一个可用的 provider"""
    providers = requests.get("https://google-api.aihang365.com/api/providers").json()
    available = [p["name"] for p in providers["providers"] if p["configured"]]
    return random.choice(available)

# 使用
provider = get_random_provider()
response = requests.post(
    "https://google-api.aihang365.com/v1/audio/speech",
    json={
        "model": "tts-1",
        "input": "测试",
        "provider": provider
    }
)
```

---

### 场景3: 按优先级使用

```python
PROVIDER_PRIORITY = [
    "platform2",  # 高配额平台优先
    "platform3",  # 次优先
    "default",    # 主Key
    "backup"      # 最后备用
]

def generate_speech_priority(text):
    """按优先级尝试 provider"""
    for provider in PROVIDER_PRIORITY:
        # 检查是否配置
        providers_info = requests.get("https://google-api.aihang365.com/api/providers").json()
        configured = any(p["name"] == provider and p["configured"]
                        for p in providers_info["providers"])

        if not configured:
            continue

        try:
            response = requests.post(
                "https://google-api.aihang365.com/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": text,
                    "provider": provider
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.content

        except:
            continue

    raise Exception("所有 provider 都不可用")
```

---

## ⚠️ 错误处理

### 错误1: Provider 不存在

**请求**:
```json
{
  "model": "tts-1",
  "input": "测试",
  "provider": "invalid"
}
```

**响应**:
```json
{
  "detail": "Unknown provider: invalid. Available: ['default', 'backup', 'platform2', 'platform3']"
}
```

---

### 错误2: Provider 未配置

**请求**:
```json
{
  "model": "tts-1",
  "input": "测试",
  "provider": "platform2"
}
```

**响应**:
```json
{
  "detail": "API Key for provider 'platform2' not configured in .env file"
}
```

---

### 错误3: 配额耗尽

**请求**:
```json
{
  "model": "tts-1-hd",
  "input": "测试",
  "provider": "default"
}
```

**响应**:
```json
{
  "detail": "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota...'}}"
}
```

**解决方案**: 切换到其他 provider

---

## 🧪 测试脚本

```python
#!/usr/bin/env python3
"""测试所有可用的 Provider"""

import requests
import json

API_URL = "https://google-api.aihang365.com"

def test_all_providers():
    # 获取可用 providers
    providers_resp = requests.get(f"{API_URL}/api/providers")
    providers_data = providers_resp.json()

    print(f"📋 可用的 Providers:")
    print(json.dumps(providers_data, indent=2, ensure_ascii=False))

    # 测试每个配置好的 provider
    for provider_info in providers_data["providers"]:
        name = provider_info["name"]
        configured = provider_info["configured"]

        if not configured:
            print(f"\n⚪ {name}: 未配置，跳过")
            continue

        print(f"\n🧪 测试 Provider: {name}")

        try:
            response = requests.post(
                f"{API_URL}/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": f"测试 {name} provider",
                    "provider": name
                },
                timeout=30
            )

            if response.status_code == 200:
                audio_size = len(response.content)
                print(f"  ✅ 成功: {audio_size:,} bytes")
            else:
                print(f"  ❌ 失败: HTTP {response.status_code}")
                print(f"     {response.text[:200]}")

        except Exception as e:
            print(f"  ❌ 异常: {e}")

if __name__ == "__main__":
    test_all_providers()
```

---

## 📝 最佳实践

### 1. 配额管理

- 为每个 provider 设置配额监控
- 当一个 provider 接近配额限制时，自动切换到下一个
- 定期检查所有 providers 的可用性

### 2. 错误处理

- 实现自动重试机制（切换 provider）
- 记录每个 provider 的失败率
- 优先使用成功率高的 provider

### 3. 负载均衡

- 轮询使用多个 providers
- 避免单个 provider 过载
- 合理分配不同优先级的任务

---

## 🚀 未来扩展

### 计划支持的功能

1. **自动故障转移**: provider 失败时自动切换
2. **配额追踪**: 实时监控每个 provider 的配额使用情况
3. **智能路由**: 根据请求类型自动选择最优 provider
4. **健康检查**: 定期检查 providers 的可用性

---

## 📚 相关文档

- [TTS Issue](../TTS_ISSUE.md) - TTS 已知问题
- [API Server](../api_server.py) - 主要代码实现
- [Test Script](../test-all-apis.py) - 完整测试脚本

---

**创建时间**: 2025-12-20
**作者**: Claude Code
**状态**: ✅ 已部署到生产环境（82.29.54.80:8100）
