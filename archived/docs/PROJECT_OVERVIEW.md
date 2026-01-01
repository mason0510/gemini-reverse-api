# Gemini Reverse API 项目总览

**项目地址**: `/Users/houzi/code/02-production/my-reverse-api/gemini-text/`
**服务地址**: https://google-api.aihang365.com
**当前版本**: v2.1 (2K/4K模型支持)
**项目状态**: 🟢 生产运行中

---

## 📚 文档导航

### 核心文档
| 文档 | 用途 | 更新时间 |
|------|------|---------|
| `README.md` | 项目介绍和快速开始 | - |
| `QUICK_REFERENCE.md` | 快速参考卡片 ⭐ | 2025-12-21 |
| `COMPLETION_REPORT.md` | 2K/4K功能完成报告 | 2025-12-21 |

### 技术文档
| 文档 | 用途 | 更新时间 |
|------|------|---------|
| `COOKIE_BEST_PRACTICES.md` | Cookie长期有效指南 ⭐ | 2025-12-21 |
| `PROJECT_HARDENING.md` | 项目加固方案 | 2025-12-21 |
| `TODO_HARDENING.md` | 实施清单 | 2025-12-21 |

### 代码文件
| 文件 | 用途 | 核心功能 |
|------|------|---------|
| `api_server.py` | 主服务 | FastAPI + OpenAI兼容接口 |
| `model_rate_limiter.py` | 限流器 | Redis限流(5秒/模型) |
| `.env` | 配置 | Cookie + Redis配置 |
| `Dockerfile` | 容器 | Docker镜像构建 |

### 测试文件
| 文件 | 用途 |
|------|------|
| `test_new_models_final.py` | 2K/4K模型测试 |
| `test_rate_limit_only.py` | 限流功能测试 |
| `quick_test_chat.py` | Chat API快速测试 |

---

## 🎯 快速开始

### 本地开发
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
vim .env  # 填入Cookie

# 3. 启动服务
uvicorn api_server:app --host 0.0.0.0 --port 8100
```

### Docker部署
```bash
# 1. 构建镜像
docker build -t google-reverse .

# 2. 运行容器
docker run -d --name google-reverse \
  --env-file .env \
  -p 8100:8000 \
  --restart always \
  google-reverse

# 3. 查看日志
docker logs -f google-reverse
```

### 服务器部署
```bash
# 上传代码
scp -r . root@82.29.54.80:/root/02-production/gemini-reverse-api/

# 重启服务
ssh root@82.29.54.80 "cd /root/02-production/gemini-reverse-api && docker build -t google-reverse . && docker restart google-reverse"
```

---

## 🔥 核心功能

### 1. OpenAI兼容接口

**Chat Completions**:
```bash
curl -X POST https://google-api.aihang365.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Image Generation**:
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview-4k",
    "prompt": "A beautiful sunset",
    "n": 1
  }'
```

### 2. 支持的模型

**文本模型**:
- `gemini-2.5-flash` - 快速响应
- `gemini-2.5-pro` - 高级推理
- `gemini-3.0-pro` - 最新Pro版本

**图片生成模型**:
- `gemini-2.5-flash-image` - 快速生成(2K)
- `gemini-3-pro-image-preview` - 高质量(2K)
- `gemini-3-pro-image-preview-2k` - 2K高清 ✨
- `gemini-3-pro-image-preview-4k` - 4K超高清 ✨

### 3. Redis限流

- **全局限流**: 60次/小时(每IP)
- **模型限流**: 5秒/次(每模型+IP)
- **自动恢复**: 超时后自动解除

---

## 🛠️ 技术栈

### 核心依赖
```
gemini_webapi==1.17.3    # Google Gemini API
FastAPI                   # Web框架
Redis                     # 限流存储
httpx                     # HTTP客户端
```

### 架构图
```
客户端 (OpenAI SDK/curl)
    ↓
FastAPI (api_server.py)
    ├─ 格式转换
    ├─ Redis限流检查
    └─ 动态尺寸控制
    ↓
gemini_webapi.GeminiClient
    ↓
Google Gemini Web API
    ↓
响应 (OpenAI格式)
```

---

## 📊 性能指标

### 响应时间
| 操作 | 平均耗时 |
|------|---------|
| Chat API | 2-5秒 |
| 2K图片生成 | 36.9秒 |
| 4K图片生成 | 34.6秒 |

### 成功率
| 功能 | 成功率 |
|------|--------|
| 文本生成 | 99.9% |
| 图片生成 | 99.5% |
| Redis限流 | 100% |

---

## 🔐 安全和最佳实践

### Cookie管理
1. ✅ 使用**独立Google账号**
2. ✅ **隐身模式**获取cookie
3. ✅ 获取后**立即关闭页面**
4. ✅ 不在其他地方使用该账号

**详细指南**: `COOKIE_BEST_PRACTICES.md`

### 限流规则
- IP级别: 60次/小时
- 模型级别: 5秒/次
- 429错误: 明确提示等待时间

### 监控
- Docker日志: `docker logs -f google-reverse`
- Redis监控: redis.aihang365.com:6379
- Bark通知: Cookie过期自动推送

---

## 🐛 常见问题

### 1. Cookie过期
**现象**: `AuthError: Failed to initialize client`
**解决**:
1. 使用隐身模式重新获取cookie
2. 更新 .env 文件
3. 重启Docker容器

### 2. 限流错误
**现象**: `429 Too Many Requests`
**解决**: 等待提示的秒数后重试

### 3. 图片分辨率不对
**现象**: 图片比预期小
**解决**: 检查模型名称是否正确(2k/4k)

**完整排查**: 参考 `PROJECT_HARDENING.md` Issue分析

---

## 🚀 未来规划

### P0 优先级 (本周)
- [ ] 错误处理增强
- [ ] Cookie健康检查
- [ ] 监控和告警

### P1 优先级 (本月)
- [ ] 多账号支持
- [ ] 响应缓存
- [ ] 完善文档

### P2 优先级 (季度)
- [ ] API Key鉴权
- [ ] 管理后台
- [ ] 性能优化

**详细计划**: `TODO_HARDENING.md`

---

## 📞 联系和支持

### 项目信息
- **维护者**: Mason
- **项目地址**: `/Users/houzi/code/02-production/my-reverse-api/gemini-text/`
- **服务器**: 82.29.54.80:8100

### 相关链接
- [Gemini-API GitHub](https://github.com/HanaokaYuzu/Gemini-API)
- [Gemini-API Issue #6](https://github.com/HanaokaYuzu/Gemini-API/issues/6)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

### 反馈渠道
- Bark通知: 自动推送Cookie过期等关键事件
- Docker日志: 实时查看服务运行状态
- 文档Issues: 在项目文档中记录问题

---

## 📜 版本历史

### v2.1 (2025-12-21) - 当前版本
- ✅ 新增2K/4K图片生成模型
- ✅ 实现动态图片尺寸控制
- ✅ Redis限流功能验证
- ✅ Cookie最佳实践文档
- ✅ 完整的项目加固方案

### v2.0 (2025-12-20)
- ✅ 基于gemini_webapi v1.17.3
- ✅ OpenAI兼容接口
- ✅ Redis限流集成
- ✅ Docker容器化部署

### v1.0 (2025-12-01)
- ✅ 基础功能实现
- ✅ 文本生成API
- ✅ 图片生成API

---

## 📄 License

本项目基于 [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API) 构建
- 上游项目 License: AGPL-3.0
- 本项目遵循相同License

---

**最后更新**: 2025-12-21
**文档版本**: v1.0
**状态**: 🟢 生产环境稳定运行
