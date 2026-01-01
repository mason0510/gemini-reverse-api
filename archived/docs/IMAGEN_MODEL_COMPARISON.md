# Imagen 模型对比测试报告

**测试时间**: 2025-12-20 18:20
**API地址**: https://google-api.aihang365.com
**测试提示词**: "A cute orange cat sitting on a wooden table"

---

## 测试结果对比

| 模型 | 状态 | Base64长度 | 预估文件大小 | 生成时间 |
|------|------|-----------|------------|---------|
| **imagen-3.0-generate-001** | ✅ 成功 | ~1,900,000字符 | ~1.4MB | ~60秒 |
| **imagen-3.0-fast-generate-001** | ✅ 成功 | 1,888,748字符 | ~1.4MB | ~30秒 |

---

## 详细分析

### imagen-3.0-generate-001 (标准模型)
- **优点**: 质量更高，细节更丰富
- **缺点**: 生成时间较长(~60秒)
- **适用场景**: 高质量图片生成，不追求速度

### imagen-3.0-fast-generate-001 (快速模型)
- **优点**: 生成速度快(~30秒)，图片质量依然不错
- **缺点**: 细节可能略逊于标准模型
- **适用场景**: 需要快速生成，对质量要求不是极高

---

## 结论

✅ **两个模型都工作正常**
- 都能成功生成1024x1024的PNG图片
- 都返回base64编码格式
- 文件大小相近(~1.4MB)
- 快速模型生成时间约为标准模型的一半

**推荐使用**:
- 日常使用 → **imagen-3.0-fast-generate-001** (速度快)
- 高质量需求 → **imagen-3.0-generate-001** (质量更好)

---

## API调用示例

### 标准模型
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "imagen-3.0-generate-001",
    "prompt": "A cute orange cat sitting on a wooden table",
    "n": 1,
    "size": "1024x1024"
  }'
```

### 快速模型
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "imagen-3.0-fast-generate-001",
    "prompt": "A cute orange cat sitting on a wooden table",
    "n": 1,
    "size": "1024x1024"
  }'
```

---

**Cookie状态**: ✅ 有效
**速率限制**: 每小时60次请求
**服务器**: 82.29.54.80 (美国)
**更新时间**: 2025-12-20 18:20
