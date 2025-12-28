# Gemini Reverse API - Claude Code 项目规范

**项目**: Gemini Reverse API (Cookie-based)
**位置**: `/Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text`
**服务器**: 82.29.54.80:8100
**容器**: google-reverse
**版本**: v4.0 (多模态增强版)
**最后更新**: 2025-12-28

---

## 📊 支持的模型列表 (13个模型 - 5大类别)

**测试环境**: 通过日本SOCKS5代理 (`socks5://root:Zhxc6545398%40@31.58.223.134:1080`)
**测试时间**: 2025-12-28
**API版本**: v4.0

### 📝 文本生成模型 (Text Models)

| 模型ID | 描述 | 状态 | 响应速度 | 推荐场景 |
|--------|------|------|---------|---------|
| **gemini-2.5-flash** | 快速响应，适合日常使用 | ✅ | ⚡⚡⚡ | 日常对话、快速问答 |
| **gemini-2.5-pro** | 擅长高阶数学和代码问题 | ✅ | ⚡⚡ | 复杂推理、代码生成 |
| **gemini-3.0-pro** | 最新Pro模型，更强推理能力 | ✅ | ⚡⚡ | 高级推理、复杂任务 |

### 🎨 图片生成模型 (Image Models)

| 模型ID | 描述 | 状态 | 分辨率 | 生成速度 | 推荐场景 |
|--------|------|------|--------|---------|---------|
| **gemini-2.5-flash-image** | 快速图片生成 | ✅ | 标准 | ⚡⚡⚡ (~30s) | 快速原型、预览 |
| **gemini-3-pro-image-preview** | 高质量图片生成 | ✅ | 2048x2048 | ⚡⚡ (~60s) | 标准高质量生成 |
| **gemini-3-pro-image-preview-2k** | 2048x2048 高清图片 | ✅ | 2K | ⚡⚡ (~60s) | 日常使用、高质量 |
| **gemini-3-pro-image-preview-4k** | 4096x4096 超高清图片 | ✅ | 4K | ⚡ (~90s) | 专业设计、超高清 |

### 🎤 语音合成模型 (TTS Models) - NEW!

| 模型ID | 描述 | 状态 | 质量 | 延迟 | 推荐场景 |
|--------|------|------|------|------|---------|
| **tts-1** | Gemini 2.5 Flash TTS | ✅ | ⭐⭐⭐ | ⚡⚡⚡ | 实时对话、快速原型 |
| **tts-1-hd** | Gemini 2.5 Pro TTS | ✅ | ⭐⭐⭐⭐⭐ | ⚡⚡ | 播客、有声读物、专业配音 |

### 📄 文档分析模型 (Document Models) - NEW!

| 模型ID | 描述 | 状态 | 推荐场景 |
|--------|------|------|---------|
| **gemini-2.5-flash-pdf** | PDF快速分析 | ✅ | 快速摘要、基础分析 |
| **gemini-2.5-pro-pdf** | PDF深度分析 | ✅ | 详细分析、数据提取 |

### 🎨 UI设计理解模型 (Design Models) - NEW!

| 模型ID | 描述 | 状态 | 推荐场景 |
|--------|------|------|---------|
| **gemini-2.5-flash-ui** | UI快速分析 | ✅ | 设计评审、组件识别 |
| **gemini-2.5-pro-ui** | UI深度分析+代码生成 | ✅ | 设计转代码、详细分析 |

---

## 🔧 技术配置

### 服务器信息

```bash
服务器IP:     82.29.54.80
API端口:      8100
容器名称:     google-reverse
镜像:         google-reverse-api
部署路径:     /root/gemini-text-api
```

### Cookie配置 (有效期短，需定期更新)

| Cookie | 有效期 | 重要性 | 更新方式 |
|--------|--------|--------|---------|
| `__Secure-1PSID` | 几个月 | 🔴 必需 | 浏览器导出 |
| `__Secure-1PSIDCC` | 几个月 | 🔴 必需 | 浏览器导出 |
| `__Secure-1PSIDTS` | ⚠️ 几小时-几天 | 🔴 必需 | 浏览器导出 |

**Cookie来源文件**: `/Users/houzi/Downloads/gemini.google.com_cookies.txt`

**更新脚本**:
```bash
# 本地快速更新Cookie到服务器
./update-server-cookies.sh /Users/houzi/Downloads/gemini.google.com_cookies.txt
```

### API Key配置

```bash
当前有效Key:  AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
备用Key:      AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
用途:         TTS语音生成 (Google AI API)
状态:         ✅ 有效 (但TTS quota已耗尽)
```

### SOCKS5代理配置

```bash
代理地址:     31.58.223.134:1080
协议:         SOCKS5
认证:         用户名密码
用户名:       root
密码:         Zhxc6545398@ (注意@符号)
URL编码:      Zhxc6545398%40 (密码中的@需要URL编码为%40)

# 完整代理URL
socks5://root:Zhxc6545398%40@31.58.223.134:1080

# 测试代理
curl --socks5 root:Zhxc6545398%40@31.58.223.134:1080 http://ipinfo.io/json
# 预期结果: "country": "JP", "city": "Tokyo"
```

---

## 🚀 API端点

### 健康检查

```bash
GET  /health                  # 服务健康检查
GET  /api/info                # API信息
GET  /api/cookies/status      # Cookie状态
GET  /api/models              # 模型列表 (13个模型)
```

### 文本生成

```bash
POST /v1/chat/completions     # OpenAI兼容对话格式
POST /v1/generate             # 简化文本生成
POST /gemini/v1beta/models/{model}:generateContent  # Gemini原生格式
```

### 图片生成

```bash
POST /v1/images/generations   # OpenAI格式图片生成
POST /v1/generate-images      # 简化图片生成
POST /v1/batch/images         # 批量图片生成
```

### 图片编辑

```bash
POST /v1/images/edit          # 自定义格式
POST /v1/images/edits         # OpenAI兼容格式
```

### 语音生成 (TTS) - NEW! ✅

```bash
POST /v1/audio/speech         # OpenAI格式TTS
GET  /v1/audio/voices         # 可用语音列表
```

**TTS使用示例**:
```bash
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "tts-1", "input": "你好，这是语音测试", "voice": "nova"}' \
  --output speech.wav
```

**支持的语音**: alloy, echo, fable, onyx, nova, shimmer

### PDF文档分析 - NEW!

```bash
POST /v1/documents/analyze    # PDF分析
POST /v1/documents/extract    # PDF数据提取
```

**使用示例**:
```bash
curl -X POST https://google-api.aihang365.com/v1/documents/analyze \
  -F "file=@document.pdf" \
  -F "prompt=请分析这个PDF的主要内容" \
  -F "detail_level=high"
```

### UI设计理解 - NEW!

```bash
POST /v1/design/analyze       # UI设计分析
POST /v1/design/to-code       # UI设计转代码
```

**使用示例**:
```bash
# 分析UI设计
curl -X POST https://google-api.aihang365.com/v1/design/analyze \
  -F "file=@ui_design.png" \
  -F "prompt=分析这个设计的布局和组件"

# 生成React代码
curl -X POST https://google-api.aihang365.com/v1/design/to-code \
  -F "file=@ui_design.png" \
  -F "framework=react" \
  -F "style_library=tailwind"
```

---

## 📦 测试脚本

### 快速测试 (所有API端点)

```bash
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text
python3 quick-test.py
```

**测试覆盖**:
- ✅ 健康检查
- ✅ 模型列表
- ✅ Chat API
- ✅ 图片生成
- ❌ TTS语音 (已知问题)

### 完整测试 (所有模型)

```bash
python3 test-all-models-complete.py
```

**测试覆盖**:
- ✅ 3个文本模型
- ✅ 4个图片模型
- ✅ 分类展示
- ✅ 通过日本代理

### 全功能测试

```bash
python3 test-all-apis.py
```

**测试覆盖**:
- 11个API端点
- 文本生成 (3种格式)
- 图片生成 (2种格式)
- 图片编辑 (3种格式)
- TTS语音 (2种质量)

---

## 🔄 Cookie更新流程

### 方法1: 自动化脚本 (推荐)

```bash
# 1. 浏览器导出Cookie到文件
/Users/houzi/Downloads/gemini.google.com_cookies.txt

# 2. 运行更新脚本
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text
./update-server-cookies.sh /Users/houzi/Downloads/gemini.google.com_cookies.txt

# 脚本会自动:
# - 提取Cookie值
# - SSH到服务器
# - 停止并删除旧容器
# - 创建新容器并注入Cookie
# - 安装google-genai SDK
# - 测试API
```

### 方法2: 手动更新

```bash
# 1. SSH到服务器
ssh root@82.29.54.80

# 2. 编辑环境变量
cd /root/gemini-text-api
nano .env

# 3. 更新以下变量
SECURE_1PSID=xxx
SECURE_1PSIDCC=xxx
SECURE_1PSIDTS=xxx

# 4. 重建容器
docker stop google-reverse
docker rm google-reverse
docker run -d \
  --name google-reverse \
  --restart unless-stopped \
  -p 8100:8000 \
  -e "SECURE_1PSID=$SECURE_1PSID" \
  -e "SECURE_1PSIDCC=$SECURE_1PSIDCC" \
  -e "SECURE_1PSIDTS=$SECURE_1PSIDTS" \
  -e "GOOGLE_AI_API_KEY=$GOOGLE_AI_API_KEY" \
  google-reverse-api

# 5. 安装SDK
docker exec google-reverse pip install google-genai

# 6. 测试
curl https://google-api.aihang365.com/health
```

---

## ⚠️ 已知问题

### 1. TTS功能 ✅ 已修复 (v4.0)

**之前的问题**:
- `tts-1`: 后端配置错误 (Model tried to generate text, but should only be used for TTS)
- `tts-1-hd`: API quota耗尽 (429 RESOURCE_EXHAUSTED)

**解决方案** (v4.0):
- 使用 "Read aloud:" 前缀强制TTS输出
- 正确配置 `responseModalities: ["AUDIO"]`
- PCM音频自动转换为WAV格式

**当前状态**: ✅ 完全可用

### 2. Cookie频繁过期

**问题**: `SECURE_1PSIDTS` 每几小时到几天就会过期

**解决方案**:
- 使用自动化脚本快速更新
- 监控 `/api/cookies/status` 端点
- 考虑实现自动Cookie刷新机制

### 3. Claude Code 断连问题 ✅ 已修复

**问题描述**:
- 使用 `claudegoogle` 命令时频繁断开连接
- 等待30秒后无响应

**根本原因**:
- `gemini-webapi` 库不支持真流式响应
- 需等待完整响应（30-60秒）后才能开始传输
- Claude Code 超时限制 ~30秒 → 连接断开

**解决方案** (已实施):
- 禁用假流式响应，使用非流式JSON响应
- 即使客户端请求 `stream=true`，也返回完整响应
- 响应时间：简单问题7秒，代码生成15-30秒

**性能表现**:
```
简单问答:    7秒  ✅
代码生成(小): 15秒 ✅
代码生成(中): 30秒 ✅
代码生成(大): 60秒+ ⚠️ 可能超时
```

**详细文档**: 参考 [STREAMING_FIX.md](STREAMING_FIX.md)

---

## 📊 限流规则

### Redis模型级别限流

```python
全局限流: 60次/小时/IP
模型限流: 同一模型5秒间隔
```

**示例**:
```
gemini-2.5-flash (第1次) → ✅ 成功
gemini-2.5-flash (第2次，立即) → ❌ 拒绝 (需等5秒)
gemini-2.5-pro (立即) → ✅ 成功 (不同模型)
```

**限流响应**:
```json
{
  "detail": "模型 gemini-2.5-flash 调用过于频繁，请等待 4.2 秒后重试"
}
```

---

## 📁 项目文件结构

```
gemini-text/
├── CLAUDE.md                          # 本文件 - 项目规范
├── .env                               # 环境变量 (Cookie, API Key)
├── quick-test.py                      # 快速API测试
├── test-all-models-complete.py        # 完整模型测试 (7个模型)
├── test-all-apis.py                   # 全功能测试 (11个端点)
├── update-server-cookies.sh           # Cookie自动更新脚本
├── README.md                          # 项目说明
├── API_DOCUMENTATION.md               # API完整文档
├── MODEL_TEST_SUMMARY.md              # 模型测试总结
├── NEW_IMAGE_MODELS.md                # 新增图片模型说明
└── docs/                              # 详细文档
    ├── GEMINI_WEBAPI_REVERSE_ENGINEERING.md
    └── FUNCTION_CALLING_ANALYSIS.md
```

---

## 🎯 开发指南

### 添加新模型

1. **服务器端** (`/root/gemini-text-api/api_server.py`):
```python
MODEL_MAP = {
    "your-model-name": "GEMINI_MODEL_ENUM",
}
```

2. **测试**:
```bash
# 添加到测试脚本
python3 test-all-models-complete.py
```

3. **更新文档**:
- 更新 `CLAUDE.md` 模型列表
- 更新 `MODEL_TEST_SUMMARY.md`

### 调试Cookie问题

```bash
# 1. 检查Cookie状态
curl https://google-api.aihang365.com/api/cookies/status

# 2. 检查容器环境变量
ssh root@82.29.54.80 "docker exec google-reverse env | grep SECURE"

# 3. 查看容器日志
ssh root@82.29.54.80 "docker logs google-reverse --tail 50"

# 4. 测试Chat API
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"test"}]}'
```


## 🔌 第三方客户端集成

### 支持的客户端类型

- ✅ Gemini原生格式客户端（如CherryStudio）
- ✅ OpenAI兼容客户端（如NextChat、ChatBox）
- ✅ 支持自定义API的聊天工具

### 快速配置

#### 方案1: Gemini原生格式（CherryStudio等）

```yaml
API类型: Gemini / Google AI
API地址: https://google-api.aihang365.com/gemini
API密钥: 任意值（如 sk-123456）
```

**可用端点**:
- `/gemini/v1beta/models` - 模型列表
- `/gemini/v1beta/models/{model}:generateContent` - 同步生成
- `/gemini/v1beta/models/{model}:streamGenerateContent` - 流式生成

#### 方案2: OpenAI兼容格式（NextChat等）

```yaml
API类型: OpenAI Compatible
API地址: https://google-api.aihang365.com/v1
API密钥: gemini-reverse-2025
```

**可用端点**:
- `/v1/models` - 模型列表
- `/v1/chat/completions` - 对话生成
- `/v1/images/generations` - 图片生成

### 防火墙配置

```bash
# 确保8100端口已开放
ssh root@82.29.54.80 'ufw allow 8100/tcp'
```

### 测试配置

```bash
# Gemini格式
curl -s https://google-api.aihang365.com/gemini/v1beta/models | head -20

# OpenAI格式
curl -s https://google-api.aihang365.com/v1/models | head -20

# 流式生成测试
curl -X POST https://google-api.aihang365.com/gemini/v1beta/models/gemini-2.5-flash:streamGenerateContent \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"你好"}]}]}'
```

**详细配置指南**: 参考 [THIRD_PARTY_INTEGRATION.md](THIRD_PARTY_INTEGRATION.md)

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | API完整文档 |
| [THIRD_PARTY_INTEGRATION.md](THIRD_PARTY_INTEGRATION.md) | 第三方客户端集成指南 |
| [STREAMING_FIX.md](STREAMING_FIX.md) | Claude Code 断连问题修复 |
| [MODEL_TEST_SUMMARY.md](MODEL_TEST_SUMMARY.md) | 模型测试总结 |
| [NEW_IMAGE_MODELS.md](NEW_IMAGE_MODELS.md) | 新增图片模型说明 |
| [HOW_TO_GET_COOKIES.md](HOW_TO_GET_COOKIES.md) | Cookie获取指南 |
| [COOKIE_BEST_PRACTICES.md](COOKIE_BEST_PRACTICES.md) | Cookie最佳实践 |
| [PROXY_SETUP.md](PROXY_SETUP.md) | 代理配置说明 |
| [REDIS_RATE_LIMIT_DEPLOYMENT.md](REDIS_RATE_LIMIT_DEPLOYMENT.md) | Redis限流部署 |
| [cookie-refresh/README.md](cookie-refresh/README.md) | Cookie管理系统文档 |
| [cookie-refresh/USAGE.md](cookie-refresh/USAGE.md) | Cookie更新快速指南 |

---

## ✅ 测试检查清单

部署或更新后必须验证:

- [x] `/health` 返回 `{"status": "ok", "version": "4.0"}`
- [x] `/api/models` 返回13个模型 (5个类别)
- [ ] `/api/cookies/status` 显示 `"valid": true` (需要更新Cookie)
- [x] TTS API测试通过 (`/v1/audio/speech`)
- [x] 语音列表正常 (`/v1/audio/voices`)
- [ ] Chat API测试通过 (需要有效Cookie)
- [ ] Image API测试通过 (需要有效Cookie)
- [ ] PDF分析测试通过 (需要有效Cookie)
- [ ] UI设计分析测试通过 (需要有效Cookie)

---

**维护者**: Mason
**最后更新**: 2025-12-28
**API版本**: v4.0
**新增功能**: TTS语音合成、PDF分析、UI设计理解
**测试结果**: TTS ✅ 已验证 | 其他功能待Cookie更新后测试
