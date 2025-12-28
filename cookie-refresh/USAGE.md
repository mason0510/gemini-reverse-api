# 快速使用指南

## 🚀 一分钟快速开始

```bash
# 1. 进入目录
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/gemini-text/cookie-refresh

# 2. 运行脚本
python3 auto-extract-from-bitbrowser-api.py

# 3. 按提示操作即可
```

## ✅ 前提条件检查清单

在运行脚本前，请确认以下事项：

- [ ] BitBrowser客户端正在运行
- [ ] BitBrowser Local Server已启动（设置 → Local Server → 启动）
- [ ] 在BitBrowser中有一个登录了Gemini的窗口
- [ ] Gemini窗口可以正常对话

## 📺 使用演示

### Step 1: 启动BitBrowser Local Server

```
打开BitBrowser
  ↓
点击设置图标
  ↓
找到"Local Server"
  ↓
点击"启动"按钮
  ↓
确认端口号（默认54345）
```

### Step 2: 准备Gemini窗口

```
在BitBrowser中创建新窗口
  ↓
窗口名称设置为包含"gemini"的名字（如"Gemini Test"）
  ↓
打开窗口，访问 https://gemini.google.com
  ↓
登录Google账号
  ↓
进行一次对话，确认功能正常
  ↓
关闭窗口（脚本会自动打开）
```

### Step 3: 运行脚本

```bash
$ python3 auto-extract-from-bitbrowser-api.py

============================================================
BitBrowser API Cookie 自动提取工具
============================================================

步骤1: 检查BitBrowser Local Server...
✅ BitBrowser Local Server运行正常

步骤2: 查找Gemini浏览器窗口...

✅ 找到 1 个Gemini窗口:
  1. [4447] Gemini Test ⚪ 未打开

步骤3: 提取Cookie...

📦 正在处理窗口: [4447] Gemini Test
  ⏳ 打开浏览器窗口...
  ⏳ 等待窗口加载...
  🍪 提取Cookie...
  ✅ 成功提取 3 个Cookie
  🛑 关闭浏览器窗口...

步骤4: 保存Cookie...

✅ Cookie已保存到: extracted_cookies.txt

📋 Cookie详情:
  __Secure-1PSID:
    值: g.a0004gikY_6Lr7pRlZlacVWwPV0VZAyvFZOq4KUmtpkoI...
    过期: 2026-12-26 00:00:00
  __Secure-1PSIDCC:
    值: AKEyXzVc6rVaDHhCLRCT-mBMN7dHJnRu2-nop47cZBJO...
    过期: 2026-12-26 00:00:00
  __Secure-1PSIDTS:
    值: sidts-CjEBflaCdf1gAoHz0RRGAkGmiPViwYxSRF451iHJC...
    过期: 2025-12-27 00:00:00

是否立即部署到服务器? (y/N): y

============================================================
正在部署到服务器...
============================================================
🛑 停止旧容器...
🚀 创建新容器...
📦 安装依赖...
🔍 测试API...
✅ 部署完成！

============================================================
🎉 自动化部署完成！
============================================================

📊 验证步骤:
  1. Chat API: curl -X POST https://google-api.aihang365.com/v1/chat/completions ...
  2. Image API: curl -X POST https://google-api.aihang365.com/v1/images/generations ...
```

## 🔍 验证部署

### 测试Chat API

```bash
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'

# 预期输出：包含"你好"回复的JSON
```

### 测试Image API

```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview",
    "prompt": "a cute cat",
    "n": 1
  }'

# 预期输出：包含图片URL或base64的JSON
```

## ❓ 常见问题

### Q1: 脚本报错"Connection refused"

**原因**: BitBrowser Local Server未启动

**解决**:
1. 打开BitBrowser客户端
2. 设置 → Local Server → 启动
3. 确认端口是54345（或修改脚本中的端口号）

### Q2: 找不到Gemini窗口

**原因**: 窗口名称不包含"gemini"关键词

**解决方式1**: 修改窗口名称
```
BitBrowser → 右键点击窗口 → 编辑 → 名称改为"Gemini Test"
```

**解决方式2**: 手动选择窗口
```
脚本会列出所有窗口，可以手动选择
```

### Q3: 提取的Cookie无效

**原因**: 窗口未登录或Cookie已过期

**解决**:
1. 手动打开窗口
2. 访问 gemini.google.com
3. 登录并进行一次对话
4. 重新运行脚本

### Q4: 部署后仍然失败

**检查步骤**:
```bash
# 1. 检查容器是否运行
ssh root@82.29.54.80 "docker ps | grep google-reverse"

# 2. 查看容器日志
ssh root@82.29.54.80 "docker logs google-reverse --tail 50"

# 3. 测试健康检查
curl https://google-api.aihang365.com/health
```

## 🎓 进阶使用

### 自定义BitBrowser端口

如果你的Local Server使用了非默认端口：

```python
# 编辑脚本
extractor = BitBrowserAPI(base_url="http://127.0.0.1:YOUR_PORT")
```

### 批量更新多个窗口

```python
# 可以扩展脚本支持批量提取多个窗口的Cookie
# 适用于多账号场景
```

### 定时自动更新

```bash
# 添加cron任务
crontab -e

# 每天凌晨2点自动更新
0 2 * * * cd /path/to/cookie-refresh && python3 auto-extract-from-bitbrowser-api.py
```

## 📞 获取帮助

如有问题，请检查:
1. [README.md](README.md) - 完整文档
2. [BitBrowser API文档](/Users/houzi/code/01-active/bitbrowser/docs/sections/jiekou/jiekou/liu-lan-qi-jie-kou.json)
3. 项目主文档: [CLAUDE.md](../../CLAUDE.md)

---

**维护者**: Mason
**最后更新**: 2025-12-26
