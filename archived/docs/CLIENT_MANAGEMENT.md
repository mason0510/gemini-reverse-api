# Gemini Client 管理机制

**更新时间**: 2025-12-19

## ✅ 当前实现：单例模式 (Singleton Pattern)

### 核心设计

```python
# 全局单例 client
gemini_client = None

# 启动时初始化一次
@app.on_event("startup")
async def startup_event():
    await init_gemini_client()  # 创建全局 client

# 所有请求共享这个 client
@app.post("/v1/chat/completions")
async def chat_completions(request, req):
    response = await gemini_client.generate_content(...)  # 复用同一个 client
```

### 优点

✅ **保持 Client ID 一致**
- 所有请求使用同一个 client 实例
- 维持稳定的会话状态
- 减少 Google 检测风险

✅ **减少资源消耗**
- 不需要每次创建新连接
- 复用 HTTP session
- 降低内存和 CPU 开销

✅ **Cookie 会话连续性**
- 保持同一个浏览器会话
- 避免频繁的身份验证
- 降低 Cookie 失效风险

## 🔄 Client 生命周期

### 1. 初始化 (Startup)

```
应用启动
  ↓
init_gemini_client()
  ↓
创建 GeminiClient()
  ↓
设置 Cookies
  ↓
设置 User-Agent
  ↓
调用 client.init()
  ↓
全局 gemini_client 就绪
```

**时机**:
- 应用启动时 (startup_event)
- 手动更新 Cookie 时 (/api/cookies/set)

### 2. 请求处理 (Runtime)

```
用户请求
  ↓
检查 gemini_client 是否存在
  ↓
频率限制检查
  ↓
随机延迟 (1-3秒)
  ↓
调用 gemini_client.generate_content()  ← 复用同一个 client
  ↓
返回响应
```

**重要**: 不会在每次请求时重新初始化 client

### 3. 错误处理

```python
try:
    response = await gemini_client.generate_content(...)
except Exception as e:
    # 检测 Cookie 过期
    if "Failed to initialize client" in error_msg or \
       "Cookies invalid" in error_msg or \
       "SECURE_1PSIDTS" in error_msg:
        # 发送 Bark 通知
        asyncio.create_task(notify_cookie_expired())
    raise HTTPException(...)
```

**不会自动重连**: 需要手动更新 Cookie 并重启服务

### 4. 关闭 (Shutdown)

```
应用关闭
  ↓
await gemini_client.close()
  ↓
释放资源
```

## 🔍 Client ID 一致性验证

### 如何验证 Client ID 保持不变

**方法1**: 检查日志中的 User-Agent
```bash
# 启动时只会看到一次 User-Agent 日志
docker logs google-reverse | grep "User-Agent"
# 输出: 🌐 使用 User-Agent: Mozilla/5.0... (只有一条)
```

**方法2**: 监控 Cookie 使用
```bash
# 所有请求都使用同一组 Cookie
# 不会看到重复的初始化日志
```

**方法3**: 检查内存中的 client 实例
```python
# 在代码中添加调试信息
print(f"Client ID: {id(gemini_client)}")  # 始终相同
```

## ⚠️ Cookie 过期处理

### 当前机制

1. **检测**: 请求失败时检查错误信息
2. **通知**: 通过 Bark 发送 iOS 推送
3. **手动**: 需要手动更新 Cookie 并重启

### Cookie 过期通知

```python
async def notify_cookie_expired():
    """Cookie过期通知（通过Bark推送到iOS）"""
    bark_key = os.getenv("BARK_KEY")
    if not bark_key:
        return

    bark_url = f"https://api.day.app/{bark_key}/Gemini%20Cookie%E8%BF%87%E6%9C%9F/请%E6%9B%B4%E6%96%B0Cookie?group=gemini-api&sound=alarm"

    async with httpx.AsyncClient() as client:
        await client.get(bark_url, timeout=5.0)
```

### 更新 Cookie 流程

```bash
# 1. 提取新 Cookie (浏览器 F12)
__Secure-1PSID=xxx
__Secure-1PSIDCC=xxx
__Secure-1PSIDTS=xxx

# 2. 更新 .env 文件
vim /root/02-production/gemini-reverse-api/.env

# 3. 重启容器
docker restart google-reverse
```

或使用自动化脚本:
```bash
./update-cookies.sh
```

## 🆚 对比：单例 vs 每次创建

| 特性 | 单例模式 (当前) | 每次创建 |
|------|----------------|----------|
| **Client ID** | ✅ 一致 | ❌ 每次不同 |
| **会话连续性** | ✅ 保持 | ❌ 断开 |
| **资源消耗** | ✅ 低 | ❌ 高 |
| **初始化开销** | ✅ 一次 | ❌ 每次 |
| **检测风险** | ✅ 低 | ❌ 高 |
| **Cookie 有效期** | ✅ 更长 | ❌ 更短 |

## 🎯 最佳实践

### 推荐做法 ✅

1. **保持单例**: 不要在请求中重新创建 client
2. **复用连接**: 所有请求共享同一个 client
3. **监控状态**: 通过 Bark 通知及时更新 Cookie
4. **定期检查**: 每天检查 `/api/cookies/status`

### 避免做法 ❌

1. **每次创建新 client**: 会导致 Client ID 频繁变化
2. **频繁重新初始化**: 增加检测风险
3. **不同请求使用不同 Cookie**: 容易触发风控
4. **忽略过期通知**: 导致服务长时间不可用

## 📊 性能指标

| 指标 | 单例模式 | 每次创建 |
|------|---------|----------|
| **初始化时间** | ~2秒 (仅启动时) | ~2秒 (每次请求) |
| **内存占用** | ~50MB | ~50MB × 请求数 |
| **并发能力** | 高 | 低 |
| **Cookie 寿命** | 数小时-数天 | 数分钟-数小时 |

## 🔧 troubleshooting

### 问题1: Cookie 频繁过期

**原因**:
- `SECURE_1PSIDTS` 有效期很短 (几小时)
- 频繁请求触发风控

**解决**:
- 降低请求频率 (30次/小时)
- 增加随机延迟 (2-5秒)
- 使用更稳定的 Cookie

### 问题2: Client 连接断开

**症状**: 所有请求返回 500 错误

**原因**:
- 网络中断
- Cookie 突然失效
- 服务器重启

**解决**:
```bash
# 检查 client 状态
curl https://google-api.aihang365.com/api/cookies/status

# 如果失效，更新 Cookie
./update-cookies.sh
```

### 问题3: 响应变慢

**原因**:
- Client session 积累了太多缓存
- 长时间运行未重启

**解决**:
```bash
# 重启容器（会重新初始化 client）
docker restart google-reverse
```

## 📝 代码位置

### 关键函数

| 函数 | 位置 | 说明 |
|------|------|------|
| `init_gemini_client()` | api_server.py:196 | 初始化 client |
| `startup_event()` | api_server.py:224 | 启动时调用 |
| `shutdown_event()` | api_server.py:239 | 关闭时清理 |
| `notify_cookie_expired()` | api_server.py:353 | Cookie 过期通知 |

### 全局变量

```python
gemini_client = None  # 单例 client (api_server.py:32)
```

## 🔗 相关文档

- [Cookie 初始化指南](./COOKIE_INIT.md)
- [速率限制配置](./RATE_LIMIT_CONFIG.md)
- [Bark 通知配置](./BARK_NOTIFICATION.md)
- [完整测试报告](./TEST_REPORT.md)

---

**维护者**: Mason
**最后验证**: 2025-12-19
**服务器**: 82.29.54.80:8100
