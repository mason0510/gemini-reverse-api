# Gemini Reverse API

**服务器**: 82.29.54.80:8100 | **容器**: google-reverse | **版本**: v4.2

## 快速使用

```bash
# 文本生成
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"你好"}]}'

# 图片生成 (OpenAI格式)
curl -X POST https://google-api.aihang365.com/v1/generate-images \
  -d '{"prompt":"一只猫","response_type":"url"}'

# 图片生成 (Gemini原生格式)
curl -X POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-3-pro-image-preview:generateContent \
  -d '{"contents":[{"parts":[{"text":"一只猫"}]}]}'
```

## 模型列表

| 类型 | 默认模型 | 备选 |
|------|---------|------|
| 文本 | `gemini-2.5-flash` | `gemini-2.5-pro`, `gemini-3.0-pro` |
| 图片 | `gemini-3-pro-image-preview` | `*-2k`, `*-4k`, `gemini-2.5-flash-image` |
| TTS | `tts-1` | `tts-1-hd` |

## 核心文件

```
api_server_v4.py      # 主服务器
├── claude_compat.py  # Claude兼容路由
├── cookie_persistence.py  # Cookie持久化
├── watermark_remover.py   # 水印去除
└── model_rate_limiter.py  # Redis限流
```

## Cookie更新

```bash
# 自动提取+部署 (需BitBrowser运行)
python3 cookie-refresh/auto-extract-from-bitbrowser-api.py
```

## 部署命令

```bash
# 上传代码
scp api_server_v4.py root@82.29.54.80:/root/gemini-text-api/

# 更新容器
ssh root@82.29.54.80 'docker cp /root/gemini-text-api/api_server_v4.py google-reverse:/app/api_server.py && docker restart google-reverse'

# 查看日志
ssh root@82.29.54.80 'docker logs google-reverse --tail 50'
```

## API端点

| 端点 | 用途 |
|------|------|
| `/health` | 健康检查 |
| `/v1/chat/completions` | OpenAI格式对话 |
| `/v1/generate-images` | 图片生成 |
| `/gemini/v1beta/models/{model}:generateContent` | Gemini原生格式 |
| `/v1/audio/speech` | TTS语音合成 |

## 已知问题

- Cookie需定期更新（PSIDTS几小时~几天过期）
- TTS依赖Google AI API Key（可能有配额限制）
