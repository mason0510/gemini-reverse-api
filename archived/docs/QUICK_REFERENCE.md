# 🚀 Gemini API 快速参考

## 📋 可用模型

### 文本对话模型
```bash
gemini-2.5-flash      # 快速（默认）
gemini-2.5-pro        # Pro版（更强推理）
gemini-3.0-pro        # 最新Pro 3.0
```

### 图片生成模型
```bash
gemini-2.5-flash-image              # 快速生成（2048²）
gemini-3-pro-image-preview          # 高质量（2048²）
gemini-3-pro-image-preview-2k       # 2K高清（2048²）✨ 新增
gemini-3-pro-image-preview-4k       # 4K超高清（4096²）✨ 新增
```

---

## 🔥 快速测试

### Chat API
```bash
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 图片生成 API
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview-4k",
    "prompt": "A beautiful sunset over mountains",
    "n": 1
  }'
```

---

## 🍪 Cookie管理

### 快速获取 Cookie（推荐方式）

1. **打开隐身模式** → 访问 https://gemini.google.com
2. **F12** → Application → Cookies
3. **复制**:
   - `__Secure-1PSID`
   - `__Secure-1PSIDCC`
   - `__Secure-1PSIDTS`
4. **更新 .env** → **立即关闭页面** ⚠️

### Cookie有效期

| 方式 | 有效期 |
|------|--------|
| ✅ 独立账号 + 隐身模式 | 1周 - 1个月 |
| ⚠️ 共用账号 + 浏览器打开 | 5-10分钟 |

**详细指南**: `COOKIE_BEST_PRACTICES.md`

---

## 🔧 服务管理

### Docker操作
```bash
# 重启服务
ssh root@82.29.54.80 "docker restart google-reverse"

# 查看日志
ssh root@82.29.54.80 "docker logs -f google-reverse"

# 查看状态
ssh root@82.29.54.80 "docker ps | grep google-reverse"
```

### 更新Cookie
```bash
# 1. 修改本地 .env
vim .env

# 2. 上传到服务器
scp .env root@82.29.54.80:/root/02-production/gemini-reverse-api/

# 3. 重启服务
ssh root@82.29.54.80 "docker restart google-reverse"
```

---

## 📊 限流规则

- **全局**: 60次/小时（每IP）
- **模型**: 5秒/次（每模型+IP）
- **错误码**: 429 Too Many Requests

---

## 🐛 常见问题

### 1. Cookie过期错误
```
AuthError: Failed to initialize client
```
**解决**: 使用隐身模式重新获取cookie，获取后立即关闭页面

### 2. 限流错误
```
429 模型调用过于频繁，请等待 X 秒后重试
```
**解决**: 等待指定秒数后重试

### 3. 连接重置
```
Connection reset by peer
```
**解决**: 检查cookie是否有效，检查网络连接

---

## 📁 项目结构

```
gemini-text/
├── api_server.py              # 主服务
├── model_rate_limiter.py      # Redis限流器
├── .env                       # 配置文件（含cookie）
├── COOKIE_BEST_PRACTICES.md   # Cookie最佳实践
├── COMPLETION_REPORT.md       # 完成报告
└── test_new_models_final.py   # 测试脚本
```

---

## 🔗 相关链接

- 服务地址: https://google-api.aihang365.com
- GitHub Issue: https://github.com/HanaokaYuzu/Gemini-API/issues/6
- Redis监控: redis.aihang365.com:6379

---

**最后更新**: 2025-12-21
**当前版本**: v2.0（含2K/4K模型支持）
