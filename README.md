# Gemini Reverse API

基于 Cookie 认证的 Gemini API 服务，提供 OpenAI 兼容格式和 Gemini 原生格式接口。

## 特性

✅ 支持 OpenAI 兼容格式 (`/v1/chat/completions`)
✅ 支持 Gemini 原生格式 (`/gemini/v1beta/models/{model}:generateContent`)
✅ 支持文本生成（Gemini 2.5/3.0 系列模型）
✅ 支持图像生成（Imagen 3 系列模型）
✅ 自动 Cookie 刷新机制
✅ Web 管理界面

## 支持的模型

### 文本模型

| 模型名称 | 说明 | 推荐场景 |
|---------|------|---------|
| **gemini-3-flash-preview** | Gemini 3.0 Flash 预览版 ⭐ | 最新快速模型 |
| **gemini-2.5-flash** | Gemini 2.5 Flash | 日常对话、快速生成 |
| **gemini-2.5-pro** | Gemini 2.5 Pro | 复杂推理任务 |
| **gemini-3.0-pro** | Gemini 3.0 Pro 预览版 | 高级推理能力 |

### 图像生成模型

| 模型名称 | 说明 | 生成速度 |
|---------|------|---------|
| **gemini-2.5-flash-image** | Imagen 3 Fast | 快速生成 |
| **gemini-3-pro-image-preview** | Imagen 3 | 高质量生成 |

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 到 `.env` 并配置必要参数：

```bash
cp .env.example .env
vim .env
```

### 2. Docker 部署

```bash
# 构建镜像
docker build -t gemini-reverse:latest .

# 运行容器
docker run -d \
  --name gemini-reverse \
  -p 8100:8100 \
  --restart unless-stopped \
  gemini-reverse:latest
```

### 3. 使用 Docker Compose

```bash
docker-compose up -d
```

## API 使用示例

### OpenAI 兼容格式

```bash
curl -X POST http://localhost:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

### Gemini 原生格式

```bash
curl -X POST http://localhost:8100/gemini/v1beta/models/gemini-3-flash-preview:generateContent \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "你好"}]
    }]
  }'
```

### 图像生成

```bash
curl -X POST http://localhost:8100/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview",
    "prompt": "a beautiful sunset over the ocean",
    "n": 1
  }'
```

## Web 管理界面

访问 `http://localhost:8100` 打开 Web 管理界面，可以：

- 查看服务状态
- 配置认证参数
- 测试模型功能

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/v1/chat/completions` | POST | OpenAI 兼容的聊天接口 |
| `/v1/images/generations` | POST | OpenAI 兼容的图像生成 |
| `/gemini/v1beta/models/{model}:generateContent` | POST | Gemini 原生格式 |
| `/api/info` | GET | 获取服务信息 |
| `/api/models` | GET | 获取支持的模型列表 |

## 配置说明

环境变量配置项（详见 `.env.example`）：

```bash
# 服务端口
PORT=8100

# API 密钥（可选，用于访问控制）
API_KEY=your-api-key-here
```

## 技术栈

- **后端框架**: FastAPI
- **异步支持**: asyncio, httpx
- **容器化**: Docker

## License

MIT License

## 致谢

本项目基于 [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API) 构建。
