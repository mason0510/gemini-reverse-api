# Bark通知功能说明

## 📱 功能概述

当Gemini API的Cookie过期导致**文本和图片生成功能不可用**时，系统会自动通过Bark发送推送通知到你的iPhone。

---

## ⚙️ 配置说明

### 1. 获取Bark Device Key

1. 在App Store下载并安装 [Bark](https://apps.apple.com/cn/app/bark/id1403753865)
2. 打开App，首页会显示你的Device Key
3. 格式示例: `KQPnaFxJo4UbrjKySY4DWg`

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```bash
# ===== Bark通知配置 =====

# Bark设备Key（必需）
BARK_KEY=KQPnaFxJo4UbrjKySY4DWg

# Bark服务器地址（可选，默认使用官方服务器）
BARK_SERVER=https://api.day.app

# 是否启用Bark通知（可选，默认启用）
ENABLE_BARK_NOTIFICATION=true
```

### 3. 重启服务

```bash
docker restart google-reverse
```

---

## 🔔 通知触发条件

系统会在以下情况下发送Bark通知：

### ✅ 触发场景

| 场景 | 触发条件 | 通知级别 |
|------|---------|---------|
| **Cookie过期** | 任何文本/图片生成请求返回Cookie错误 | timeSensitive |

### 🚫 不触发通知的情况

- TTS（语音生成）失败 - 因为TTS使用API Key，不依赖Cookie
- 健康检查、API信息等管理接口
- 请求频率限制（HTTP 429）

---

## 📬 通知内容示例

当Cookie过期时，你的iPhone会收到以下推送：

```
标题: ⚠️ Gemini API Cookie过期

内容:
文本和图片生成功能不可用
时间: 2025-12-19 17:30:45
服务器: 82.29.54.80:8100
需要更新Cookie

铃声: alarm（闹钟）
级别: timeSensitive（时效性通知，会突破专注模式）
分组: gemini-api
```

---

## 🛡️ 防重复通知机制

为避免通知轰炸，系统内置了**1小时冷却时间**：

- ✅ Cookie第一次过期 → 立即发送通知
- ⚠️ 1小时内再次失败 → 不重复发送
- ✅ 1小时后仍未修复 → 再次发送通知

**冷却时间配置**（代码中修改）:
```python
BARK_COOLDOWN = 3600  # 秒，默认1小时
```

---

## 🔧 测试通知

### 方法1: 手动测试（推荐）

```bash
# 测试通知发送
curl -G "https://api.day.app/YOUR_BARK_KEY" \
  --data-urlencode "title=测试通知" \
  --data-urlencode "body=Gemini API Bark通知功能测试" \
  --data-urlencode "sound=alarm" \
  --data-urlencode "level=timeSensitive"
```

### 方法2: 模拟Cookie过期

**⚠️ 警告**: 这会导致服务真的不可用

```bash
# 临时修改Cookie为无效值
ssh root@82.29.54.80
cd /root/02-production/gemini-reverse-api
sed -i 's/SECURE_1PSID=.*/SECURE_1PSID=invalid/' .env
docker restart google-reverse

# 触发通知
curl -X POST http://127.0.0.1:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"test"}]}'

# 查看日志确认通知已发送
docker logs google-reverse | grep "Bark通知"

# 恢复正确的Cookie
# （粘贴正确的Cookie值后重启）
```

---

## 📊 通知日志

系统会在容器日志中记录Bark通知的发送状态：

```bash
# 查看通知日志
docker logs google-reverse | grep "Bark"

# 示例输出
📱 Bark通知已发送: ⚠️ Gemini API Cookie过期
⚠️ Bark通知发送失败: HTTP 404
❌ Bark通知异常: Connection timeout
```

---

## ❓ 常见问题

### Q1: 没有收到通知？

**检查清单**：
1. ✅ 确认 `BARK_KEY` 配置正确
2. ✅ 确认 `ENABLE_BARK_NOTIFICATION=true`
3. ✅ 检查iPhone网络连接
4. ✅ 确认Bark App在后台运行
5. ✅ 检查"设置→通知→Bark"是否允许通知
6. ✅ 查看容器日志: `docker logs google-reverse | grep Bark`

### Q2: 通知延迟很高？

**可能原因**：
- APNs服务延迟（苹果服务器问题）
- iPhone处于省电模式
- 网络环境不佳

**解决方案**：
- 通知级别已设置为`timeSensitive`，会尽快送达
- 确保iPhone网络畅通

### Q3: 通知太频繁？

**调整冷却时间**：

编辑 `api_server.py`，修改冷却时间：
```python
BARK_COOLDOWN = 7200  # 改为2小时
```

或者直接禁用通知：
```bash
# .env文件
ENABLE_BARK_NOTIFICATION=false
```

### Q4: 想要自定义通知内容？

编辑 `api_server.py` 中的 `notify_cookie_expired()` 函数：

```python
async def notify_cookie_expired():
    """通知Cookie已过期（带冷却时间）"""
    now = time.time()
    if now - last_bark_notification["cookie_expired"] < BARK_COOLDOWN:
        return

    await send_bark_notification(
        "🚨 自定义标题",  # ← 修改标题
        f"自定义内容\n"   # ← 修改内容
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        level="active"  # ← 修改级别（passive/active/timeSensitive/critical）
    )
    last_bark_notification["cookie_expired"] = now
```

### Q5: 如何使用自建Bark服务器？

修改 `.env` 配置：
```bash
BARK_SERVER=http://your-bark-server.com:8080
```

---

## 🎯 通知级别说明

| 级别 | 说明 | 使用场景 |
|------|------|---------|
| **passive** | 被动通知，不点亮屏幕 | 不重要的提醒 |
| **active** | 立即显示，点亮屏幕 | 普通通知 |
| **timeSensitive** | 时效性通知，突破专注模式 | **Cookie过期**（当前使用）⭐ |
| **critical** | 关键告警，突破勿扰模式 | 需特殊权限 |

---

## 🔗 相关文档

- **Bark官方文档**: https://bark.day.app/
- **Bark GitHub**: https://github.com/Finb/Bark
- **完整Bark API文档**: `/Users/houzi/code/02-production/bark-notice/Bark-API-完整文档-v1.1-20251205.md`

---

## 📝 更新日志

### v1.0 (2025-12-19)
- ✅ 实现Cookie过期自动通知
- ✅ 支持1小时冷却时间防重复通知
- ✅ 使用timeSensitive级别确保及时送达
- ✅ 支持自定义Bark服务器
- ✅ 完整的错误日志记录

---

**维护者**: Mason
**最后更新**: 2025-12-19
**服务器**: 82.29.54.80:8100
