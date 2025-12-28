# Cookie 自动提取工具

**创建时间**: 2025-12-26
**版本**: v2.0.0 - BitBrowser API Edition

## 📋 工具列表

### 1. **auto-extract-from-bitbrowser-api.py** ⭐ 推荐

通过BitBrowser本地API自动提取Cookie（无需解密）

**优点**:
- ✅ 完全自动化（1分钟完成）
- ✅ 无需密码学解密
- ✅ 实时获取最新Cookie
- ✅ 支持自动部署

**前提条件**:
1. BitBrowser客户端正在运行
2. Local Server已启动（设置 → Local Server）
3. 已在BitBrowser中登录gemini.google.com

**使用方法**:
```bash
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text/cookie-refresh

# 运行脚本
python3 auto-extract-from-bitbrowser-api.py

# 按照提示操作:
# 1. 选择Gemini窗口
# 2. 脚本自动打开窗口并提取Cookie
# 3. 选择是否部署到服务器
```

**工作流程**:
```
1. 连接BitBrowser Local Server (http://127.0.0.1:54345)
   └── 检查连接状态

2. 查找Gemini浏览器窗口
   └── 搜索名称/平台/备注包含"gemini"的窗口

3. 提取Cookie
   ├── 如果窗口未打开 → 自动打开窗口
   ├── 通过API获取实时Cookie (/browser/cookies/get)
   └── 过滤出必需的3个Cookie

4. 保存到文件
   └── extracted_cookies.txt (Netscape格式)

5. 部署到服务器（可选）
   └── SSH到82.29.54.80并重建容器
```

---

### 2. **extract-cookies-javascript.html**

网页版Cookie提取工具

**使用方法**:
1. 在BitBrowser中访问 gemini.google.com
2. 将此HTML文件拖到浏览器中打开
3. 点击"提取Cookie"按钮
4. 复制生成的cookies.txt内容

**优点**:
- ✅ 简单直观
- ✅ 无需编程知识

**缺点**:
- ⚠️ 需要手动操作
- ⚠️ 需要手动复制粘贴

---

## 🚀 快速开始

### 首次使用

1. **启动BitBrowser Local Server**

   打开BitBrowser客户端:
   ```
   设置 → Local Server → 启动
   默认端口: 54345
   ```

2. **确认Gemini窗口已登录**

   在BitBrowser中:
   - 访问 https://gemini.google.com
   - 成功登录并进行过对话
   - 确认可以正常使用

3. **运行自动提取脚本**

   ```bash
   cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text/cookie-refresh
   python3 auto-extract-from-bitbrowser-api.py
   ```

4. **验证部署**

   ```bash
   # 测试Chat API
   curl -X POST https://google-api.aihang365.com/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"hi"}]}'

   # 测试Image API
   curl -X POST https://google-api.aihang365.com/v1/images/generations \
     -H "Content-Type: application/json" \
     -d '{"model":"gemini-3-pro-image-preview","prompt":"a cute cat"}'
   ```

---

## 📊 Cookie有效期

| Cookie | 有效期 | 重要性 |
|--------|--------|--------|
| `__Secure-1PSID` | ~1年 | 🔴 必需 |
| `__Secure-1PSIDCC` | ~1年 | 🔴 必需 |
| `__Secure-1PSIDTS` | ⚠️ 6-24小时 | 🔴 必需 |

**更新建议**:
- **PSIDTS有效期短** → 建议每24小时更新一次
- 设置定时任务自动更新

---

## ⚙️ 定时自动更新

### 方法1: cron定时任务

```bash
# 编辑crontab
crontab -e

# 添加以下行（每24小时执行一次）
0 0 * * * cd /path/to/cookie-refresh && python3 auto-extract-from-bitbrowser-api.py

# 或者每12小时执行一次
0 */12 * * * cd /path/to/cookie-refresh && python3 auto-extract-from-bitbrowser-api.py
```

### 方法2: 创建wrapper脚本

```bash
#!/bin/bash
# 功能: 定时更新Gemini Cookie
# 关键词: auto-update, cron, gemini-cookie

set -e

cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text/cookie-refresh

# 运行提取脚本（自动选择第一个窗口，自动部署）
echo "y" | python3 auto-extract-from-bitbrowser-api.py

# 记录更新时间
echo "Last updated: $(date)" >> update.log
```

---

## 🔧 故障排查

### 问题1: 无法连接到BitBrowser Local Server

**错误信息**:
```
❌ 无法连接到BitBrowser Local Server: [Errno 61] Connection refused
```

**解决方案**:
1. 确认BitBrowser客户端正在运行
2. 检查Local Server是否已启动:
   ```
   BitBrowser → 设置 → Local Server → 查看状态
   ```
3. 确认端口号正确（默认54345）

### 问题2: 未找到Gemini浏览器窗口

**错误信息**:
```
❌ 未找到Gemini相关的浏览器窗口
```

**解决方案**:
1. 在BitBrowser中创建新窗口
2. 访问 https://gemini.google.com
3. 窗口名称/备注中包含"gemini"关键词

### 问题3: 缺少必需的Cookie

**错误信息**:
```
❌ 缺少必需的Cookie: __Secure-1PSID, __Secure-1PSIDCC, __Secure-1PSIDTS
```

**解决方案**:
1. 确保在BitBrowser中已成功登录Gemini
2. 进行一次对话，激活Cookie
3. 刷新页面后重试

### 问题4: 部署后API仍然失败

**检查步骤**:
```bash
# 1. 检查容器状态
ssh root@82.29.54.80 "docker ps | grep google-reverse"

# 2. 查看容器日志
ssh root@82.29.54.80 "docker logs google-reverse --tail 50"

# 3. 测试Cookie状态
curl https://google-api.aihang365.com/api/cookies/status
```

---

## 📚 BitBrowser API参考

### 核心API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | POST | 健康检查 |
| `/browser/list` | POST | 获取浏览器窗口列表 |
| `/browser/detail` | POST | 获取窗口详情 |
| `/browser/open` | POST | 打开浏览器窗口 |
| `/browser/close` | POST | 关闭浏览器窗口 |
| `/browser/cookies/get` | POST | 获取实时Cookie |
| `/browser/cookies/set` | POST | 设置Cookie |
| `/browser/cookies/clear` | POST | 清除Cookie |

### API文档位置

完整API文档位于:
```
/Users/houzi/code/01-active/bitbrowser/docs/sections/jiekou/jiekou/liu-lan-qi-jie-kou.json
```

---

## 📝 文件说明

| 文件 | 说明 |
|------|------|
| `auto-extract-from-bitbrowser-api.py` | ⭐ 主要脚本（推荐使用） |
| `extract-cookies-javascript.html` | 网页版提取工具 |
| `extracted_cookies.txt` | 提取的Cookie文件 |
| `README.md` | 本文档 |

---

## 🔗 相关资源

- [BitBrowser官网](https://www.bitbrowser.cn/)
- [BitBrowser API文档](https://doc2.bitbrowser.cn/jiekou.html)
- [Gemini Reverse API项目](../../CLAUDE.md)

---

**维护者**: Mason
**最后更新**: 2025-12-26
