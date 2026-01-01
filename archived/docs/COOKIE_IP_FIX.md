# Cookie IP 一致性问题 - 正确解决方案

## 问题根源

```
Cookie获取时的IP: 183.192.93.255 (中国上海移动 - ClashX代理)
服务器部署IP: 82.29.54.80 (美国)
→ Gemini检测到IP不一致 → 拒绝请求
```

## ✅ 正确解决方案

### 在美国IP下重新获取Cookie

**步骤1: 切换ClashX到美国节点**

1. 打开ClashX
2. 选择一个**美国节点**（最好选择地理位置接近的）
3. 确保是全局模式

**步骤2: 验证出口IP**

```bash
curl https://ifconfig.me
# 应该显示美国IP，例如: 123.45.67.89 (US)
```

**步骤3: 访问Gemini并登录**

1. 清除浏览器Gemini相关Cookie
2. 访问 https://gemini.google.com
3. 登录你的Google账号
4. 确保能正常使用Gemini

**步骤4: 导出Cookie**

使用浏览器扩展导出Cookie（推荐）：
- Chrome: "Get cookies.txt LOCALLY"
- Firefox: "cookies.txt"

或者手动复制：
1. 打开开发者工具 (F12)
2. Application → Cookies → https://gemini.google.com
3. 复制以下Cookie值：
   - `__Secure-1PSID`
   - `__Secure-1PSIDCC`
   - `__Secure-1PSIDTS`

**步骤5: 部署到服务器**

```bash
# 更新.env文件
vim .env
# 粘贴新的Cookie值

# 部署
./update-cookies.sh
```

**步骤6: 验证**

```bash
# 测试Cookie状态
curl https://google-api.aihang365.com/api/cookies/status | jq .

# 测试文本生成
curl -X POST https://google-api.aihang365.com/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "model": "gemini-2.5-flash"}' | jq .
```

## 💡 为什么不用代理？

**你的想法是对的！**

- ✅ 服务器在美国，可以直接访问Gemini
- ✅ 不需要代理
- ✅ 只需要Cookie是在美国IP获取的

我之前的代理方案是错误的，会增加复杂度和不稳定性。

## 📝 Cookie管理最佳实践

### 选项A: 每次从美国IP获取（推荐）

- 优点: 简单，IP一定匹配
- 缺点: 需要手动切换代理节点

### 选项B: 使用服务器的固定IP

如果你能在服务器上安装桌面环境和浏览器（不推荐，太重）：
```bash
# 不推荐，仅供参考
apt install -y xvfb chromium-browser
# 使用headless浏览器获取Cookie
```

### 选项C: 使用API Key代替Cookie（最稳定）⭐

如果你有Google AI API Key，可以只用API Key：

```bash
# .env
GOOGLE_AI_API_KEY=AIzaSy...

# TTS等功能会使用API Key
# 不再依赖Cookie
```

## 🎯 推荐方案

**短期**: 切换到美国节点重新获取Cookie（5分钟）
**长期**: 申请Google AI API Key，减少对Cookie的依赖

## ⚠️ 注意事项

1. **Cookie有效期**: 通常1-2周，需要定期更新
2. **IP变化**: 如果服务器IP改变，需要重新获取Cookie
3. **账号安全**: 不要在公开场合暴露Cookie
4. **Bark通知**: Cookie过期时会收到通知（如果配置了BARK_KEY）
