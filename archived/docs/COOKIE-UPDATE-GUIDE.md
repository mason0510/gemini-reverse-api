# Gemini Cookie 更新指南

## 📅 更新记录

| 更新时间 | 有效期至 | 更新者 | 备注 |
|---------|---------|-------|------|
| 2025-12-18 | ~2026-01-17 | Mason | 初始配置 |

## 🔑 核心Cookie说明

| Cookie名称 | 必需性 | 有效期 | 用途 |
|-----------|--------|-------|------|
| `__Secure-1PSID` | ✅ 必需 | ~1年 | 核心认证Token |
| `__Secure-1PSIDCC` | ⭐ 推荐 | ~1年 | 会话安全验证 |
| `__Secure-1PSIDTS` | ⭐ 推荐 | ~30天 | 时间戳验证，**最短有效期** |

**过期判断**：当 `__Secure-1PSIDTS` 过期时，需要更新所有Cookie。

---

## 🔄 Cookie更新流程

### 方法1: Web界面导入（推荐）

1. **导出Cookie**
   ```bash
   # 使用浏览器插件 "Get cookies.txt LOCALLY"
   # Chrome扩展地址: https://chrome.google.com/webstore/detail/cclelndahbckbenkjhflpdbgdldlbecc

   # 访问 gemini.google.com
   # 点击插件图标 → Export → gemini.google.com
   # 保存为 cookies.txt
   ```

2. **导入到系统**
   ```bash
   # 访问 https://google-api.aihang365.com
   # 点击"配置Cookie" → "cookies.txt"标签
   # 粘贴 cookies.txt 内容 → 保存
   ```

3. **验证**
   ```bash
   curl -s https://google-api.aihang365.com/api/cookies/status | jq
   # 应该返回: {"valid": true, "message": "Cookie有效，客户端已就绪"}
   ```

### 方法2: 直接替换备份文件

1. **更新备份文件**
   ```bash
   # 编辑项目中的备份文件
   vim /Users/houzi/code/02-production/my-reverse-api/gemini-text/cookies-backup.txt

   # 替换整个文件内容为新导出的 cookies.txt
   ```

2. **通过Web界面重新配置**
   ```bash
   # 访问 https://google-api.aihang365.com
   # 使用新的Cookie配置
   ```

---

## ⚠️ Cookie失效症状

| 症状 | 原因 | 解决方案 |
|-----|------|---------|
| API返回503 "客户端未初始化" | Cookie未配置 | 重新配置Cookie |
| API返回401或403 | Cookie已过期 | 更新Cookie |
| 图片生成失败，返回403 | Cookie过期或无效 | 更新Cookie |
| 文本生成正常，图片失败 | 图片需要额外权限 | 检查Cookie完整性 |

---

## 🔍 Cookie有效期检查

```bash
# 检查 __Secure-1PSIDTS 过期时间（Unix时间戳）
# 在 cookies-backup.txt 中查找:
# .google.com	TRUE	/	TRUE	1797582308	__Secure-1PSIDTS	...
#                                    ^^^^^^^^^^
#                                    这是过期时间戳

# 转换为可读时间
date -r 1797582308  # macOS
# 或
date -d @1797582308  # Linux

# 输出: 2026年1月17日左右
```

---

## 📦 备份文件位置

| 文件 | 路径 | 用途 |
|------|-----|------|
| cookies-backup.txt | `/Users/houzi/code/02-production/my-reverse-api/gemini-text/` | 完整Cookie备份 |
| .env.example | 同上 | 环境变量示例 |
| COOKIE-UPDATE-GUIDE.md | 同上 | 本指南 |

---

## 🔐 安全提示

⚠️ **重要安全事项**：

1. **不要公开分享Cookie**
   - Cookie包含完整的账户认证信息
   - 泄露后他人可以完全访问你的Gemini账户

2. **定期更新**
   - 建议每30天主动更新一次
   - 避免突然失效影响服务

3. **备份加密存储**
   - 敏感文件使用加密存储
   - 不要提交到公开Git仓库

4. **访问控制**
   - API服务器仅限内网或可信IP访问
   - 使用防火墙限制端口访问

---

## 🛠️ 故障排查

### 问题1: Cookie配置后仍然失败

```bash
# 1. 检查Cookie格式
# cookies.txt 必须是标准的Netscape格式
# 每行格式: 域名 <TAB> TRUE/FALSE <TAB> 路径 <TAB> TRUE/FALSE <TAB> 过期时间 <TAB> 名称 <TAB> 值

# 2. 检查必需Cookie是否存在
grep "__Secure-1PSID" cookies-backup.txt
grep "__Secure-1PSIDCC" cookies-backup.txt
grep "__Secure-1PSIDTS" cookies-backup.txt

# 3. 重启服务
ssh root@82.29.54.80 "docker restart google-reverse"
```

### 问题2: Web界面导入失败

```bash
# 1. 检查Docker容器状态
ssh root@82.29.54.80 "docker ps | grep google-reverse"

# 2. 查看容器日志
ssh root@82.29.54.80 "docker logs google-reverse --tail 50"

# 3. 手动测试API
curl -X POST https://google-api.aihang365.com/api/cookies \
  -H "Content-Type: application/json" \
  -d '{"cookies": {"__Secure-1PSID": "your_cookie_value"}}'
```

---

## 📞 联系方式

如有问题，请联系：Mason

**文档版本**: v1.0
**最后更新**: 2025-12-18
**下次检查**: 2026-01-15 (预计Cookie过期前)
