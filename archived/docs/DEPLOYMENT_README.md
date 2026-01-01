# Gemini Text API 部署和测试指南

## 🚀 服务器部署状态

| 组件 | 状态 | 地址 |
|------|------|------|
| API服务 | ✅ 运行中 | http://82.29.54.80:8765 |
| 域名访问 | ⚠️ 待配置 | https://gemini-text.satoshitech.xyz |
| Docker容器 | ✅ 运行中 | gemini-text-api |
| 端口 | ✅ 8765 | 内部端口: 8000 |

## ⚙️ 支持的模型

| 模型ID | 模型名称 | 描述 |
|--------|----------|------|
| `gemini-2.5-flash` | Gemini 2.5 Flash | 快速响应，适合日常使用 |
| `gemini-2.5-pro` | Gemini 2.5 Pro | 擅长高阶数学和代码问题 |
| `gemini-3.0-pro` | Gemini 3.0 Pro | 最新Pro模型，更强推理能力 |

**注意**: `gemini-3-flash-preview` 在 `gemini-webapi` 库中尚未支持，待库更新后添加。

## 📝 Cookie配置

### ⚠️ 当前Cookie状态
Cookie已过期，需要重新获取。错误提示：
```
Failed to initialize client. SECURE_1PSIDTS could get expired frequently
```

### 方法1: Web界面配置（推荐）

1. **访问配置页面**
   ```
   http://82.29.54.80:8765
   ```

2. **获取Cookie**
   - 打开 https://gemini.google.com/ 并登录
   - 按F12打开开发者工具
   - 进入 Application → Cookies → https://gemini.google.com
   - 复制以下3个Cookie值：
     - `__Secure-1PSID`
     - `__Secure-1PSIDCC`
     - `__Secure-1PSIDTS`

3. **在Web界面中粘贴Cookie值**
   - 点击"保存Cookie"
   - 等待客户端重新初始化

### 方法2: 更新服务器.env文件

```bash
# 1. 编辑服务器上的.env文件
ssh root@82.29.54.80
cd /root/gemini-text-api
nano .env

# 2. 更新以下内容
SECURE_1PSID=你的__Secure-1PSID值
SECURE_1PSIDCC=你的__Secure-1PSIDCC值
SECURE_1PSIDTS=你的__Secure-1PSIDTS值

# 3. 重启容器
docker restart gemini-text-api

# 4. 查看日志确认初始化成功
docker logs -f gemini-text-api
```

## 🧪 测试脚本

### 本地测试远程API

```bash
cd /Users/houzi/code/02-production/my-reverse-api/gemini-text
python3 test_remote_api.py
```

测试内容：
- ✅ 健康检查 (`/health`)
- ✅ 所有模型文本生成 (`/v1/generate`)
- ✅ OpenAI兼容格式 (`/v1/chat/completions`)
- ✅ Gemini原生格式 (`/gemini/v1beta/models/{model}:generateContent`)

### 服务器本地测试

```bash
# SSH到服务器
ssh root@82.29.54.80

# 在容器内运行测试
cd /root/gemini-text-api
docker exec gemini-text-api python test_models.py
```

## 🌐 API端点

### 1. 简单文本生成

```bash
curl -X POST http://82.29.54.80:8765/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "你好，请介绍你自己",
    "model": "gemini-2.5-flash"
  }'
```

### 2. OpenAI兼容格式

```bash
curl -X POST http://82.29.54.80:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [
      {"role": "user", "content": "解释量子纠缠"}
    ]
  }'
```

### 3. Gemini原生格式

```bash
curl -X POST http://82.29.54.80:8765/gemini/v1beta/models/gemini-3.0-pro:generateContent \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "什么是人工智能？"}]
    }]
  }'
```

### 4. 图片生成

```bash
curl -X POST http://82.29.54.80:8765/v1/generate-images \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的猫咪在阳光下睡觉",
    "model": "gemini-2.5-flash",
    "count": 1
  }'
```

## 🔧 容器管理

### 查看日志
```bash
ssh root@82.29.54.80 "docker logs -f gemini-text-api"
```

### 重启服务
```bash
ssh root@82.29.54.80 "docker restart gemini-text-api"
```

### 重新构建
```bash
# 本地同步代码
rsync -avz --exclude '__pycache__' \
  /Users/houzi/code/02-production/my-reverse-api/gemini-text/ \
  root@82.29.54.80:/root/gemini-text-api/

# 服务器上重建
ssh root@82.29.54.80 "cd /root/gemini-text-api && docker build -t gemini-text-api . && docker stop gemini-text-api && docker rm gemini-text-api && docker run -d --name gemini-text-api --restart unless-stopped -p 8765:8000 --network nginx-proxy --env-file .env -e VIRTUAL_HOST=gemini-text.satoshitech.xyz -e VIRTUAL_PORT=8000 -e LETSENCRYPT_HOST=gemini-text.satoshitech.xyz -e LETSENCRYPT_EMAIL=houziyu2019@gmail.com gemini-text-api"
```

## 📊 测试结果示例

更新Cookie后的预期测试结果：

```
============================================================
Test Summary
============================================================
✅ PASS - gemini-2.5-flash
✅ PASS - gemini-2.5-pro
✅ PASS - gemini-3.0-pro
✅ PASS - OpenAI Format
✅ PASS - Gemini Native Format

Total: 5 | Passed: 5 | Failed: 0
```

## 🚨 常见问题

### Q: 为什么所有请求都返回500错误？
A: Cookie已过期，需要重新获取并配置。`__Secure-1PSIDTS` 会频繁过期（几小时到几天）。

### Q: 如何验证Cookie是否有效？
A: 访问 http://82.29.54.80:8765/api/cookies/status

### Q: gemini-3-flash-preview模型不可用？
A: 该模型尚未在 `gemini-webapi` 库中定义，待库更新后支持。

### Q: 域名访问无法连接？
A: 确保nginx-proxy网络配置正确，并且Let's Encrypt证书已生成。

## 📚 相关文档

- [Cookie获取指南](HOW_TO_GET_COOKIES.md)
- [API文档](API_DOCUMENTATION.md)
- [项目总结](PROJECT_SUMMARY.md)

---

**最后更新**: 2025-12-18
**服务器**: 82.29.54.80 (美国)
**维护者**: Mason
