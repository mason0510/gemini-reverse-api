# Gemini Cookie IP一致性问题解决方案

## 问题现象

```
Cookie获取IP: 183.192.93.255 (中国上海，通过ClashX代理)
服务器部署IP: 82.29.54.80 (美国)
结果: Cookie验证失败 ❌ IP不匹配
```

## 根本原因

Gemini的Cookie验证**不仅检查Cookie本身的有效性，还会检查请求IP是否与Cookie获取时的IP一致**。

## 解决方案

### 方案1：在服务器上配置代理（推荐）⭐

让服务器也通过相同的代理出口访问Gemini API。

#### 步骤1：启动服务器上的xray客户端

```bash
# SSH到服务器
ssh root@82.29.54.80

# 检查xray配置
cat /usr/local/etc/xray/config.json

# 启动xray（如果配置正确）
systemctl start xray
systemctl enable xray

# 验证xray监听端口
netstat -tlnp | grep xray
# 应该看到类似: 127.0.0.1:1080 (socks5)
#             或: 127.0.0.1:8118 (http)
```

#### 步骤2：修改Docker容器使用代理

编辑 `docker-compose.yml` 或启动脚本，添加环境变量：

```yaml
services:
  gemini-reverse:
    environment:
      - HTTP_PROXY=http://127.0.0.1:8118
      - HTTPS_PROXY=http://127.0.0.1:8118
      - NO_PROXY=localhost,127.0.0.1
```

或者在 `update-cookies.sh` 中添加：

```bash
docker run -d \
  --name google-reverse \
  -p 8100:8100 \
  -e HTTP_PROXY=http://host.docker.internal:8118 \
  -e HTTPS_PROXY=http://host.docker.internal:8118 \
  gemini-reverse-api:latest
```

#### 步骤3：验证代理生效

```bash
# 在容器内测试
docker exec google-reverse curl -s https://ifconfig.me
# 应该输出: 183.192.93.255 (或你的代理出口IP)
```

### 方案2：重新获取Cookie（临时方案）

如果不想配置代理，可以在服务器上直接获取Cookie：

```bash
# 1. 在服务器上安装桌面环境（不推荐，太重）
# 2. 或者使用你的代理节点，在一个和服务器相同出口IP的环境中获取Cookie
# 3. 或者暂时接受API限制，不使用Cookie功能，只用API Key
```

### 方案3：使用SSH隧道（最简单的临时方案）⭐⭐⭐

让服务器通过SSH隧道使用你本地的ClashX代理：

```bash
# 在本地电脑执行（保持运行）
ssh -R 8118:127.0.0.1:7890 root@82.29.54.80 -N

# 这会在服务器的8118端口创建一个到你本地7890端口的隧道
# 然后在服务器的Docker容器中配置:
# HTTP_PROXY=http://127.0.0.1:8118
```

**注意**：这个方案需要保持SSH连接，适合临时测试。

## 验证步骤

### 1. 验证代理配置

```bash
# 在容器内测试出口IP
docker exec google-reverse curl -s https://ifconfig.me

# 应该输出: 183.192.93.255 (和获取Cookie时的IP一致)
```

### 2. 验证Cookie有效性

```bash
# 测试Gemini API
curl -X POST https://google-api.aihang365.com/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "model": "gemini-2.5-flash"}'

# 应该返回文本响应，而不是Cookie错误
```

## 推荐配置

**最终推荐：方案3（SSH隧道）+ 方案1（长期部署时配置xray）**

1. **立即测试**：使用SSH隧道让Cookie工作
2. **长期运行**：配置服务器上的xray客户端

## 安全提示

- ⚠️ 不要在公开的GitHub仓库中暴露代理配置
- ⚠️ 使用SSH隧道时注意连接稳定性
- ✅ 推荐使用systemd管理代理服务，确保自动重启
