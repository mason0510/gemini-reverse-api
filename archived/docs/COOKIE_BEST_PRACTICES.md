# Gemini Cookie 最佳实践指南

基于 [Gemini-API Issue #6](https://github.com/HanaokaYuzu/Gemini-API/issues/6) 的经验总结

## 🔥 核心问题

`__Secure-1PSIDTS` 会快速过期(5-10分钟),导致API调用失败:
```
AuthError: Failed to initialize client. SECURE_1PSIDTS could get expired frequently
```

## ✅ 解决方案

### 方案1: 独立Google账号 (推荐)

**原理**: Cookie快速过期的根本原因是**同一账号在其他地方被使用**

**步骤**:
1. 创建一个**专用的Google账号**(仅用于API调用)
2. 不要在浏览器或其他地方使用这个账号访问 gemini.google.com
3. 获取cookie后,立即关闭所有相关页面

**效果**: Cookie可持续使用 **1周到1个月**

---

### 方案2: 隐身模式获取Cookie (有效)

**步骤**:
1. 打开浏览器**隐身/无痕模式**
2. 访问 https://gemini.google.com 并登录
3. 打开开发者工具 (F12) → Network标签
4. 刷新页面,在Network中找到请求
5. 复制 `__Secure-1PSID` 和 `__Secure-1PSIDTS`
6. **立即关闭隐身窗口**

**关键**: 获取cookie后立即关闭,不要继续使用

---

### 方案3: Cookie自动刷新 (已实现)

我们的实现中已经集成了 `gemini_webapi` 库,它支持:
- ✅ 自动检测cookie过期
- ✅ 后台自动刷新cookie
- ✅ 持久化保存新cookie

**配置**: 无需额外配置,库会自动处理

---

## 📋 Cookie获取详细步骤

### 使用隐身模式 (推荐)

```bash
1. 打开浏览器隐身标签页
2. 访问 https://gemini.google.com
3. 登录Google账号
4. 等待页面完全加载
5. 按 F12 打开开发者工具
6. 切换到 "Application" 或 "Storage" 标签
7. 左侧选择 Cookies → https://gemini.google.com
8. 找到以下cookie并复制值:
   - __Secure-1PSID
   - __Secure-1PSIDCC (可选,但建议也复制)
   - __Secure-1PSIDTS
9. 更新到 .env 文件
10. ⚠️ 立即关闭隐身窗口
```

### 注意事项

⚠️ **必须做**:
- ✅ 使用独立账号(不在其他地方使用)
- ✅ 获取cookie后立即关闭页面
- ✅ 使用隐身模式获取

❌ **禁止做**:
- ❌ 在获取cookie后继续使用该账号访问 gemini.google.com
- ❌ 在多个设备/浏览器同时使用同一账号
- ❌ 频繁刷新cookie (会加速过期)

---

## 🔧 .env 配置示例

```env
# 从隐身模式获取的cookie
SECURE_1PSID=g.a000xxx...
SECURE_1PSIDCC=AKEyXzxxx...
SECURE_1PSIDTS=sidts-CjEBxxx...

# Redis配置(用于限流)
REDIS_HOST=redis.aihang365.com
REDIS_PORT=6379
REDIS_PASSWORD=your_password
```

---

## 📊 Cookie生命周期

| 使用方式 | Cookie有效期 | 原因 |
|---------|-------------|------|
| **独立账号 + 隐身模式** | 1周 - 1个月 | ✅ 最佳实践 |
| **独立账号 + 正常模式** | 1周左右 | ✅ 较好 |
| **共用账号 + 浏览器打开** | 5-10分钟 | ❌ 快速过期 |
| **频繁访问 gemini.google.com** | 几分钟 | ❌ 立即失效 |

---

## 🚀 自动化部署建议

### Docker部署时的Cookie管理

**方案A**: 环境变量 (适合单服务器)
```bash
# .env
SECURE_1PSID=xxx
SECURE_1PSIDCC=xxx
SECURE_1PSIDTS=xxx
```

**方案B**: 配置文件挂载 (适合多服务器)
```yaml
# docker-compose.yml
services:
  gemini-api:
    volumes:
      - ./cookies.json:/app/cookies.json:ro
    environment:
      - COOKIE_FILE=/app/cookies.json
```

**方案C**: 集中式存储 (适合集群)
- Redis存储cookie
- 定期从专用账号刷新
- 所有节点共享cookie

---

## 🔍 故障排查

### 问题: Cookie立即过期

**检查清单**:
```bash
□ 是否使用了独立账号?
□ 获取cookie后是否关闭了页面?
□ 是否在其他地方使用该账号访问了gemini.google.com?
□ 是否使用了隐身模式?
□ cookie值是否完整复制(没有截断)?
```

### 问题: 某些账号没有 `__Secure-1PSIDTS`

**解决方案**:
1. 刷新页面,等待几秒
2. `__Secure-1PSIDTS` 会在首次访问后生成
3. 如果始终没有,可能是账号特殊情况,尝试:
   - 重新登录
   - 切换到隐身模式
   - 使用其他账号

---

## 📈 监控Cookie状态

### 检查Cookie是否有效

```bash
# 测试API是否正常
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 正常: 返回200
# Cookie过期: 返回500 "Failed to initialize client"
```

### Docker日志监控

```bash
# 查看服务日志
docker logs -f google-reverse

# 正常启动:
# ✅ Gemini客户端初始化成功!

# Cookie失效:
# ⚠️ Gemini客户端初始化失败: AuthError
```

---

## 🎯 最佳实践总结

1. **使用专用Google账号** (仅用于API,不在其他地方使用)
2. **隐身模式获取cookie** (获取后立即关闭)
3. **不要频繁更新cookie** (让库自动刷新)
4. **监控cookie状态** (设置告警)
5. **准备备用账号** (主账号失效时快速切换)

---

## 参考资源

- [Gemini-API GitHub Issue #6](https://github.com/HanaokaYuzu/Gemini-API/issues/6)
- [gemini_webapi 文档](https://github.com/HanaokaYuzu/gemini-webapi)
- 本项目: `/Users/houzi/code/02-production/my-reverse-api/gemini-text/`

---

**更新时间**: 2025-12-21
**状态**: ✅ 已验证有效
