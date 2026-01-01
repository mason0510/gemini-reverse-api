# 归档文件

此目录包含历史版本代码、旧文档和不常用脚本。

## 目录结构

```
archived/
├── old-versions/     # 旧版本代码
│   ├── api_server.py
│   ├── api_server_fixed.py
│   ├── api_server_updated.py
│   ├── api_server_v3.py
│   ├── app.py
│   └── watermark_remover.py
│
├── docs/             # 历史文档
│   ├── *_REPORT.md   # 各种报告
│   ├── *_FIX.md      # 修复记录
│   └── ...
│
├── scripts/          # 不常用脚本
│   ├── clash-*.sh    # Clash代理相关
│   ├── deploy-*.sh   # 部署脚本
│   └── update-*.sh   # 更新脚本
│
└── test-scripts/     # 旧测试脚本
    ├── test-all-apis.py
    ├── test-provider-mode.py
    └── ...
```

## 查找历史信息

如需查找历史实现细节，可在此目录搜索：

```bash
# 搜索关键词
grep -r "关键词" archived/

# 查看特定文档
cat archived/docs/STREAMING_FIX.md
```

## 恢复旧版本

如需恢复旧版本代码：

```bash
# 复制到主目录
cp archived/old-versions/api_server_v3.py ./

# 或使用git历史
git log --oneline -- api_server.py
```

---

*归档时间: 2026-01-01*
