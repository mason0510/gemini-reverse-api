# Gemini Reverse API

基于 Cookie 认证的 Gemini API 服务，提供 OpenAI 兼容格式和 Gemini 原生格式接口。

## 特性

✅ 支持 OpenAI 兼容格式 (`/v1/chat/completions`)
✅ 支持 Gemini 原生格式 (`/gemini/v1beta/models/{model}:generateContent`)
✅ 支持文本生成（Gemini 2.5/3.0 系列模型）
✅ 支持图像生成（Imagen 3 + Gemini 3 Pro）
✅ 支持2K/4K高清图片生成 ✨ (v2.1新增)
✅ **参考图编辑** - 基于已有图片生成新图片 ✨ (v2.2新增)
✅ **R2云存储** - 图片上传返回公共URL ✨ (v2.2新增)
✅ **自动去水印** - 反向Alpha混合算法去除Gemini水印 ✨ (v3.1新增)
✅ Redis智能限流（全局+模型级别）✨
✅ 自动 Cookie 刷新机制
✅ Web 管理界面

**最新版本**: v3.1 (2025-12-26)
**技术栈**: 基于 [gemini_webapi v1.17.3](https://github.com/HanaokaYuzu/Gemini-API)

## 支持的模型

### 文本模型

| 模型名称 | 说明 | 推荐场景 |
|---------|------|---------|
| **gemini-3-flash-preview** | Gemini 3.0 Flash 预览版 ⭐ | 最新快速模型 |
| **gemini-2.5-flash** | Gemini 2.5 Flash | 日常对话、快速生成 |
| **gemini-2.5-pro** | Gemini 2.5 Pro | 复杂推理任务 |
| **gemini-3.0-pro** | Gemini 3.0 Pro 预览版 | 高级推理能力 |

### 图像生成模型

| 模型名称 | 说明 | 分辨率 | 生成速度 |
|---------|------|--------|---------|
| **gemini-2.5-flash-image** | Imagen 3 Fast | 2048² | 快速生成 |
| **gemini-3-pro-image-preview** | Imagen 3 | 2048² | 高质量 |
| **gemini-3-pro-image-preview-2k** ✨ | Gemini 3 Pro (2K) | 2048² | ~37秒 |
| **gemini-3-pro-image-preview-4k** ✨ | Gemini 3 Pro (4K) | 4096² | ~35秒 |

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

**所有生成的图片自动去除 Gemini 水印** ✨

```bash
# 返回 base64（默认）
curl -X POST http://localhost:8100/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful sunset over the ocean"
  }'

# 返回 R2 公共 URL
curl -X POST http://localhost:8100/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute cat",
    "response_type": "url"
  }'
```

**去水印技术**: 使用反向Alpha混合算法，基于 Gemini SynthID 水印原理逆向求解原图，毫秒级处理速度。

### 参考图编辑 ✨ (重点功能)

基于参考图生成新图片，支持风格转换、背景替换、元素添加等场景。

**Bash 示例**:
```bash
# 准备参考图 base64
IMAGE_BASE64=$(base64 -i input.png)

# 调用 API 进行图片编辑
curl -X POST http://localhost:8100/v1/images/edit \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"将背景改为蓝色天空\",
    \"image\": \"data:image/png;base64,${IMAGE_BASE64}\",
    \"response_type\": \"url\"
  }"
```

**Python 示例**:
```python
import requests
import base64

# 读取参考图
with open("input.png", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

# 调用 API
response = requests.post(
    "http://localhost:8100/v1/images/edit",
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
| `"将背景改为白色"` | 更换背景颜色 |
| `"转换为水彩画风格"` | 风格转换 |
| `"移除图片中的文字"` | 去除水印/文字 |
| `"添加一只小狗"` | 添加元素 |
| `"将白天改为夜晚"` | 光线/时间调整 |

## Web 管理界面

访问 `http://localhost:8100` 打开 Web 管理界面，可以：

- 查看服务状态
- 配置 Cookie 参数
- 测试模型功能
- 查看 API 文档

## 项目结构

```
.
├── api_server.py          # 核心 API 服务
├── app.py                 # 简化版入口
├── web/                   # Web 管理界面
│   ├── index.html
│   └── static/
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/info` | GET | 获取服务信息 |
| `/api/models` | GET | 获取支持的模型列表 |
| `/v1/models` | GET | OpenAI兼容模型列表 |
| `/api/cookies` | POST | 更新 Cookie 配置 |
| `/v1/chat/completions` | POST | OpenAI 兼容的聊天接口 |
| `/v1/generate` | POST | 简化文本生成 |
| `/v1/generate-images` | POST | 图片生成（支持base64/url返回） |
| `/v1/images/generations` | POST | OpenAI 兼容图像生成 |
| `/v1/images/edit` | POST | **参考图编辑** ✨ |
| `/v1/images/edits` | POST | 参考图编辑（别名） |
| `/gemini/v1beta/models/{model}:generateContent` | POST | Gemini 原生格式 |

## 配置说明

环境变量配置项（详见 `.env.example`）：

```bash
# 服务端口
PORT=8100

# API 密钥（可选，用于访问控制）
API_KEY=your-api-key-here

# Cookie 配置（需要从浏览器获取）
SECURE_1PSID=your-cookie-value
SECURE_1PSIDCC=your-cookie-value
SECURE_1PSIDTS=your-cookie-value
```

## 技术栈

- **后端框架**: FastAPI
- **异步支持**: asyncio, httpx
- **Cookie 管理**: 自动刷新机制
- **容器化**: Docker

## 限制说明

- 依赖 Google 账号的 Gemini 网页版配额
- Cookie 有效期约 1-2 个月（建议使用独立账号，详见下方文档）
- 单账号有 QPS 限制
- **限流规则**: 全局60次/小时，单模型5秒/次
- 不支持流式输出（计划支持）

## 📚 完整文档

**强烈建议阅读以下文档以获得最佳体验**:

| 文档 | 说明 | 优先级 |
|------|------|--------|
| `API_DOCUMENTATION.md` | **完整API文档** ⭐ | P0 |
| `COOKIE_BEST_PRACTICES.md` | Cookie长期有效指南 ⭐ | P0 |
| `PROJECT_OVERVIEW.md` | 项目完整总览 | P0 |
| `QUICK_REFERENCE.md` | API快速参考 | P1 |
| `COMPLETION_REPORT.md` | 2K/4K功能完成报告 | P1 |
| `PROJECT_HARDENING.md` | 项目加固和Issue分析 | P2 |
| `TODO_HARDENING.md` | 优化实施清单 | P2 |

## 常见问题

**Q: Cookie 从哪里获取？**
A: 使用**隐身模式**登录 Google Gemini 网页版，从浏览器开发者工具中提取相关 Cookie。详见 `COOKIE_BEST_PRACTICES.md`

**Q: Cookie 多久失效？为什么会快速过期？**
A:
- ✅ **正确使用**: 独立账号 + 隐身模式获取 → 可用1周到1个月
- ❌ **快速失效**: 同一账号在浏览器同时使用 → 5-10分钟失效
- 详细说明参考 [Gemini-API Issue #6](https://github.com/HanaokaYuzu/Gemini-API/issues/6) 和 `COOKIE_BEST_PRACTICES.md`

**Q: 支持哪些模型？**
A: 支持 Gemini 2.5/3.0 系列文本模型 和 Imagen 3/Gemini 3 Pro 图像模型。完整列表见上方"支持的模型"部分。

**Q: 2K和4K模型有什么区别？**
A: 主要是输出分辨率不同：
- 2K: 2048x2048像素
- 4K: 4096x4096像素（更清晰，文件更大）

**Q: 限流错误怎么办？**
A: 收到429错误时，等待提示的秒数后重试。限流规则：全局60次/小时，单模型5秒/次。

## License

AGPL-3.0 (与上游项目 [gemini_webapi](https://github.com/HanaokaYuzu/Gemini-API) 保持一致)

## 🙏 致谢

本项目基于 [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API) (gemini_webapi) 构建
- ⭐ 1.7k stars
- 📦 PyPI: gemini_webapi v1.17.3
- 📄 License: AGPL-3.0

---

**服务地址**: https://google-api.aihang365.com
**最后更新**: 2025-12-26
**当前版本**: v3.1 (自动去水印 + 智能重试 + 并发支持)
**状态**: 🟢 生产环境稳定运行

