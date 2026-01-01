# Claude Code Skills - Gemini Reverse API 项目

**项目**: Gemini Reverse API
**路径**: `/Users/houzi/code/02-production/my-reverse-api/gemini-text/`
**更新时间**: 2025-12-20

---

## 📚 本项目积累的关键技能

### 1. 🔐 Cookie 认证机制与 IP 一致性

**核心发现**: Cookie 频繁失效的根本原因

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Cookie 几小时就失效 | 获取 Cookie 的 IP ≠ 使用 Cookie 的 IP | 通过服务器代理获取 Cookie |
| Google 检测到异常 | `SECURE_1PSIDTS` 用于风控检测 | 保持 IP 一致性 |

**技术要点**:

```
正确的Cookie获取流程：
1. 在服务器上部署代理（如 Squid、Clash）
2. 浏览器通过服务器代理访问 Gemini
3. F12 导出 Cookie（此时 IP = 服务器 IP）
4. 服务器使用该 Cookie（IP 一致）
5. Cookie 稳定有效（几天不失效）

错误的做法：
❌ 本地浏览器获取 Cookie（本地 IP）
❌ 服务器使用该 Cookie（服务器 IP ≠ 本地 IP）
❌ Google 检测到异常 → Cookie 快速失效
```

**相关文件**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/extract-cookies-from-browser.sh`
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/CLIENT_MANAGEMENT.md`

**参考案例**:
- 2025-12-20: Cookie 失效问题排查与解决
- 使用美国服务器代理获取的 Cookie 后，测试成功率从 21% 提升到 93%

---

### 2. 🐳 Docker 服务部署与自动化脚本

**核心技能**: 编写高效的部署脚本

**`update-cookies.sh` 脚本结构**:

```bash
#!/bin/bash
# 更新Cookie并重新部署服务

# 1. 上传配置文件
scp .env api_server.py root@82.29.54.80:/root/02-production/gemini-reverse-api/

# 2. SSH到服务器执行部署
ssh root@82.29.54.80 << 'ENDSSH'
  cd /root/02-production/gemini-reverse-api

  # 停止并删除旧容器
  docker stop google-reverse && docker rm google-reverse

  # 重新构建镜像
  docker build -t gemini-reverse-api .

  # 启动新容器
  docker run -d --name google-reverse -p 8100:8000 gemini-reverse-api

  # 等待启动
  sleep 5

  # 验证Cookie状态
  curl http://localhost:8100/api/cookies/status
ENDSSH
```

**最佳实践**:

- ✅ 使用 `HEREDOC` (`<< 'ENDSSH'`) 执行远程多行命令
- ✅ 部署后立即验证服务状态
- ✅ 提供清晰的进度提示（🔄、✅、❌ emoji）
- ✅ 错误时自动回滚

**相关文件**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/update-cookies.sh`
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/Dockerfile`

---

### 3. 🧪 完整的 API 测试框架

**核心技能**: 编写可维护的测试脚本

**测试脚本设计模式**:

```python
def print_section(title):
    """打印测试分类标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_test(name):
    """打印单个测试项"""
    print(f"\n📤 {name}")
    print("-" * 80)

def print_result(status_code, success=True):
    """打印测试结果"""
    if success:
        print(f"✅ 成功 - HTTP {status_code}")
    else:
        print(f"❌ 失败 - HTTP {status_code}")
```

**测试覆盖**:

| 类别 | 端点数 | 测试重点 |
|------|--------|---------|
| 健康检查 | 4 | 基础连接、Cookie 状态 |
| 文本生成 | 3 | OpenAI 格式、Gemini 原生格式、简化格式 |
| 图片生成 | 2 | Imagen4 生成、响应格式处理 |
| 图片编辑 | 3 | Base64 编码、临时文件清理 |
| TTS 语音 | 2 | 音频生成、quota 限制 |

**相关文件**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/test-all-apis.py`
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/TEST_REPORT.md`

---

### 4. 🔄 单例模式与客户端生命周期管理

**核心发现**: 不要在每次请求时重新初始化 client

**错误做法** ❌:

```python
@app.on_event("startup")
async def startup_event():
    await init_gemini_client()
    await gemini_client.init()  # ❌ 启动时验证 Cookie

# 每次请求都会触发重新验证
@app.post("/v1/chat/completions")
async def chat_completions(request):
    response = await gemini_client.generate_content(...)
```

**正确做法** ✅:

```python
@app.on_event("startup")
async def startup_event():
    await init_gemini_client()
    # ✅ 不在启动时调用 init()
    # 让库的 @running 装饰器在第一次请求时自动调用

# 第一次请求时验证，后续请求复用
@app.post("/v1/chat/completions")
async def chat_completions(request):
    response = await gemini_client.generate_content(...)
```

**技术原理**:

```
gemini-webapi 库的 @running 装饰器:
1. 检查 client._running 标志
2. 如果 False，调用 client.init() 验证 Cookie
3. 验证成功后，设置 _running = True
4. 后续请求跳过验证，直接复用

问题原因:
- 启动时调用 init() 失败 → _running = False
- 每次请求都重试 init() → Cookie 频繁验证 → 触发风控
```

**相关文件**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/api_server.py:196-224`
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/CLIENT_MANAGEMENT.md`

---

### 5. 📝 文档驱动开发 (Documentation-Driven Development)

**核心技能**: 将复杂问题沉淀为可复用的文档

**文档结构设计**:

```
gemini-text/
├── docs/
│   ├── GEMINI_WEBAPI_REVERSE_ENGINEERING.md  # 技术参考
│   └── features/                              # 功能收敛文档
├── CLIENT_MANAGEMENT.md                       # 客户端管理机制
├── COOKIE_INIT.md                             # Cookie 初始化指南
├── RATE_LIMIT_CONFIG.md                       # 速率限制配置
├── BARK_NOTIFICATION.md                       # Bark 通知配置
├── IMAGE_EDIT_API.md                          # 图片编辑 API
├── TTS_ISSUE.md                               # TTS 问题记录
├── TEST_REPORT.md                             # 完整测试报告
└── CLAUDECODE_SKILLS.md                       # Claude Code 技能积累
```

**文档模板**:

每个重要功能完成后，必须创建收敛文档，包含：

1. **功能概述**: 该功能解决了什么问题
2. **技术实现**: 关键代码片段与架构设计
3. **测试记录**: 测试用例与结果
4. **问题记录**: 踩过的坑与解决方案
5. **依赖清单**: 外部依赖与配置要求
6. **使用文档**: 如何使用该功能

**最佳实践**:

- ✅ 表格 > 纯文字（快速对比信息）
- ✅ 代码示例 + 注释（可直接复用）
- ✅ 问题 + 原因 + 解决方案（三段式）
- ✅ 时间线记录（方便追溯）

---

### 6. 🔍 问题排查与根因分析

**核心技能**: 系统化的问题诊断方法

**排查流程**:

```
1. 现象观察
   - 收集错误日志
   - 记录失败率
   - 确认影响范围

2. 假设验证
   - 提出多个可能原因
   - 设计验证实验
   - 逐一排除

3. 根因定位
   - 深入源码分析
   - 理解底层机制
   - 找到真正原因

4. 解决方案
   - 修复代码
   - 验证效果
   - 文档记录
```

**案例**:

**问题**: Cookie 频繁失效

**排查过程**:

1. **现象**: Cookie 几小时就失效，需要频繁更新
2. **假设1**: Cookie 本身过期 → ❌ 验证发现有效期到 2026 年
3. **假设2**: Google 服务器检测异常 → ✅ 可能
4. **深入分析**:
   - 研究 `SECURE_1PSIDTS` 的作用（会话时间戳，用于风控）
   - 发现 IP 地址不一致（浏览器 IP ≠ 服务器 IP）
5. **根因**: Google 检测到同一 Cookie 从不同 IP 使用 → 标记为可疑 → 快速失效
6. **解决**: 通过服务器代理获取 Cookie（IP 一致性）
7. **验证**: 成功率从 21% 提升到 93%

**相关文档**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/CLIENT_MANAGEMENT.md:212-224`

---

### 7. 🌐 逆向工程 API 的最佳实践

**核心技能**: 从 `gemini_webapi` 库学到的架构设计

**分层架构**:

```
┌─────────────────────────────────────────┐
│            应用接口层                   │
│  (FastAPI 端点、OpenAI 兼容格式)        │
├─────────────────────────────────────────┤
│            功能模块层                   │
│  (文本生成、图片生成、图片编辑、TTS)    │
├─────────────────────────────────────────┤
│            数据类型层                   │
│  (Pydantic 模型、类型验证)              │
├─────────────────────────────────────────┤
│            基础设施层                   │
│  (GeminiClient、Cookie 管理、日志)      │
└─────────────────────────────────────────┘
```

**关键技术点**:

1. **认证机制**:
   - Cookie 自动刷新（后台任务）
   - 多来源 Cookie 导入（浏览器 / 手动）
   - 认证失败重试策略

2. **异步架构**:
   - 基于 `httpx.AsyncClient`
   - 自动关闭闲置连接（`auto_close` + `close_delay`）
   - 统一的 `@running` 装饰器

3. **类型安全**:
   - Pydantic 模型定义所有数据结构
   - 输入输出严格验证
   - 自动生成文档（FastAPI）

4. **错误处理**:
   - 专门的异常类（`AuthError`、`APIError`）
   - 统一的重试逻辑
   - 详细的错误日志

**参考文档**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/docs/GEMINI_WEBAPI_REVERSE_ENGINEERING.md`

---

### 8. 📊 速率限制与反检测策略

**核心技能**: 平衡性能与安全的速率控制

**当前配置**:

```python
MAX_REQUESTS_PER_HOUR = 60  # 每小时最多 60 次请求
MIN_DELAY = 1.0              # 最小延迟 1 秒
MAX_DELAY = 3.0              # 最大延迟 3 秒
```

**优化建议**:

```python
# 降低 Google 风控检测
MAX_REQUESTS_PER_HOUR = 30   # 降低到 30 次/小时
MIN_DELAY = 2.0              # 增加到 2 秒
MAX_DELAY = 5.0              # 增加到 5 秒
```

**User-Agent 模拟**:

```python
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",  # Chrome on Mac
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",       # Chrome on Windows
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",  # Safari on Mac
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) ...",  # Firefox
    "Mozilla/5.0 (X11; Linux x86_64) ...",                 # Chrome on Linux
]
```

**最佳实践**:

- ✅ 滑动窗口计数（而非固定时间窗口）
- ✅ 随机延迟（模拟人类操作）
- ✅ 轮换 User-Agent（增加逼真度）
- ⚠️ Cookie IP 一致性（最关键）

**相关文件**:
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/api_server.py:90-125`
- `/Users/houzi/code/02-production/my-reverse-api/gemini-text/RATE_LIMIT_CONFIG.md`

---

## 🎯 总结：可复用的技能清单

### 技术技能

- [x] Cookie 认证逆向与 IP 一致性维护
- [x] Docker 服务部署与自动化脚本编写
- [x] 完整的 API 测试框架设计
- [x] 单例模式与客户端生命周期管理
- [x] 异步 Python 编程（FastAPI + httpx）
- [x] Pydantic 数据模型与类型验证
- [x] 速率限制与反检测策略
- [x] 错误处理与重试机制

### 工程技能

- [x] 文档驱动开发（DDD）
- [x] 问题排查与根因分析
- [x] 系统化的测试方法（健康检查 → 功能测试 → 压力测试）
- [x] 版本管理与变更记录
- [x] 服务监控与告警（Bark 通知）

### 架构技能

- [x] 分层架构设计（接口层 → 功能层 → 数据层 → 基础设施层）
- [x] OpenAI 格式兼容封装
- [x] 多格式支持（OpenAI、Gemini 原生、简化格式）
- [x] 可扩展的功能模块设计

---

## 📖 相关文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 技术参考 | `docs/GEMINI_WEBAPI_REVERSE_ENGINEERING.md` | gemini_webapi 库架构分析 |
| 客户端管理 | `CLIENT_MANAGEMENT.md` | 单例模式与生命周期 |
| Cookie 初始化 | `COOKIE_INIT.md` | Cookie 获取与配置 |
| 速率限制 | `RATE_LIMIT_CONFIG.md` | 速率控制与反检测 |
| 测试报告 | `TEST_REPORT.md` | 完整测试结果 |
| 图片编辑 | `IMAGE_EDIT_API.md` | 图片编辑功能文档 |
| TTS 问题 | `TTS_ISSUE.md` | TTS quota 限制 |
| Bark 通知 | `BARK_NOTIFICATION.md` | Cookie 过期通知 |

---

**技能记录者**: Claude Code
**记录时间**: 2025-12-20
**项目状态**: ✅ 生产环境运行中（82.29.54.80:8100）
**测试成功率**: 93% (13/14 端点正常工作)
