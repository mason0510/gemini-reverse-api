# Cookie初始化与持久化指南

## 当前Cookie状态

**服务器**: 82.29.54.80
**容器**: google-reverse
**端口**: 8100
**状态**: ✅ Cookie有效

## Cookie提取方法

### 方法1: 使用浏览器DevTools (推荐)

1. 访问 https://gemini.google.com 并登录
2. 打开浏览器开发者工具 (F12)
3. 切换到 **Application** 标签
4. 左侧选择 **Cookies** → `https://gemini.google.com`
5. 找到以下三个Cookie并复制其值:
   - `__Secure-1PSID`
   - `__Secure-1PSIDCC`
   - `__Secure-1PSIDTS`

### 方法2: 使用Cookie导出扩展

推荐扩展: **EditThisCookie** (Chrome/Edge)

1. 安装扩展后访问 gemini.google.com
2. 点击扩展图标
3. 导出为 Netscape 格式
4. 提取上述三个Cookie的值

## Cookie更新流程

### 1. 更新本地.env文件

编辑 `/Users/houzi/code/02-production/my-reverse-api/gemini-text/.env`:

```bash
SECURE_1PSID=你的__Secure-1PSID值
SECURE_1PSIDCC=你的__Secure-1PSIDCC值
SECURE_1PSIDTS=你的__Secure-1PSIDTS值
GOOGLE_AI_API_KEY=AIzaSyAV3pi1L5rEkBGQvp9O7ffc0mTOVud0GhE
```

### 2. 同步到服务器

```bash
# 从本地项目目录执行
cd /Users/houzi/code/02-production/my-reverse-api/gemini-text

# 同步.env文件到服务器
scp .env root@82.29.54.80:/root/02-production/gemini-reverse-api/.env

# 同步api_server.py到服务器
scp api_server.py root@82.29.54.80:/root/02-production/gemini-reverse-api/api_server.py
```

### 3. 重启Docker容器

```bash
ssh root@82.29.54.80 "
cd /root/02-production/gemini-reverse-api && \
docker stop google-reverse && \
docker rm google-reverse && \
docker build --no-cache -t gemini-reverse-api:latest . && \
docker run -d \
  --name google-reverse \
  -p 8100:8100 \
  --restart unless-stopped \
  gemini-reverse-api:latest
"
```

### 4. 验证Cookie状态

```bash
# 等待5秒让容器完全启动
sleep 5

# 检查Cookie状态
curl https://google-api.aihang365.com/api/cookies/status
```

预期输出:
```json
{
  "valid": true,
  "message": "Cookie有效，客户端已就绪"
}
```

## 快速更新脚本

为了方便快速更新Cookie,可以使用以下脚本:

```bash
#!/bin/bash
# 文件: update-cookies.sh

set -e

SERVER="root@82.29.54.80"
PROJECT_DIR="/root/02-production/gemini-reverse-api"
LOCAL_DIR="/Users/houzi/code/02-production/my-reverse-api/gemini-text"

echo "🔄 开始更新Cookie..."

# 1. 同步.env文件
echo "📤 上传.env文件..."
scp $LOCAL_DIR/.env $SERVER:$PROJECT_DIR/.env

# 2. 同步api_server.py
echo "📤 上传api_server.py..."
scp $LOCAL_DIR/api_server.py $SERVER:$PROJECT_DIR/api_server.py

# 3. 重启容器
echo "🔄 重启Docker容器..."
ssh $SERVER "
cd $PROJECT_DIR && \
docker stop google-reverse && \
docker rm google-reverse && \
docker build --no-cache -t gemini-reverse-api:latest . && \
docker run -d \
  --name google-reverse \
  -p 8100:8100 \
  --restart unless-stopped \
  gemini-reverse-api:latest
"

# 4. 等待启动
echo "⏳ 等待容器启动..."
sleep 5

# 5. 验证状态
echo "✅ 验证Cookie状态..."
curl -s https://google-api.aihang365.com/api/cookies/status | python3 -m json.tool

echo ""
echo "🎉 Cookie更新完成!"
```

保存为 `/Users/houzi/code/02-production/my-reverse-api/gemini-text/update-cookies.sh` 并添加执行权限:

```bash
chmod +x /Users/houzi/code/02-production/my-reverse-api/gemini-text/update-cookies.sh
```

使用方法:
```bash
cd /Users/houzi/code/02-production/my-reverse-api/gemini-text
./update-cookies.sh
```

## Cookie过期监控

项目已集成Bark通知,当Cookie过期时会自动推送通知到iOS设备。

### Bark配置

检查 `.env` 中的Bark配置:
```bash
BARK_KEY=你的Bark Key
BARK_GROUP=gemini-api
```

### 监控端点

```bash
# 查看Cookie状态
curl https://google-api.aihang365.com/api/cookies/status

# 响应示例
{
  "valid": true,           # Cookie是否有效
  "message": "Cookie有效，客户端已就绪"
}
```

## 故障排查

### 问题1: Cookie状态显示无效

```bash
# 检查容器日志
ssh root@82.29.54.80 "docker logs google-reverse --tail 50"

# 检查.env文件是否正确加载
ssh root@82.29.54.80 "docker exec google-reverse env | grep SECURE"
```

### 问题2: Docker容器无法启动

```bash
# 查看容器状态
ssh root@82.29.54.80 "docker ps -a | grep google-reverse"

# 查看完整日志
ssh root@82.29.54.80 "docker logs google-reverse"
```

### 问题3: API返回403错误

可能原因:
1. Cookie已过期 → 重新提取Cookie并更新
2. API Key泄露被封 → 使用新的API Key
3. 请求频率过高 → 检查rate limiting配置

## Cookie有效期说明

- `__Secure-1PSID`: 长期有效 (通常几个月)
- `__Secure-1PSIDCC`: 中期有效 (通常几周)
- `__Secure-1PSIDTS`: 短期有效 (通常几天) ⚠️ 最容易过期

**建议**: 每周检查一次Cookie状态,发现无效立即更新。

## 当前配置

**最后更新时间**: 2025-12-19

**当前Cookie值** (存储在服务器 `/root/02-production/gemini-reverse-api/.env`):
```
SECURE_1PSID=g.a0004gjKrz5ksJslz502stoellB9icpACLsPflO5tB1DtTTM4Vm1gJn6TG7FV6KIND-JIVLE1wACgYKASESAQ4SFQHGX2MiOmhvqHdgXWWpEfXPklC1MBoVAUF8yKq5GwcfeVBhUMVOOSC48vug0076
SECURE_1PSIDCC=AKEyXzVfJtpoCc7hD8b2Bgx3J409F2LRwQrEiZlfBf5gr_7OXaPYDPmbDnK1HB-ypTmngoiGzg
SECURE_1PSIDTS=sidts-CjIBflaCdRdwkXRuGZU10VID7JCcaeEAB0xrL5DR4D5izg6O9F1KBTxz-uJbNFirByzC_xAA
```

**TTS API Key**:
```
GOOGLE_AI_API_KEY=AIzaSyAV3pi1L5rEkBGQvp9O7ffc0mTOVud0GhE
```

**状态**: ✅ 有效

## 相关文档

- [图片编辑API文档](IMAGE_EDIT_API.md)
- [Bark推送通知配置](BARK_NOTIFICATION.md)
- [速率限制配置](RATE_LIMIT_CONFIG.md)
