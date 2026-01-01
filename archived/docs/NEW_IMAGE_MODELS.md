# 新增图片生成模型说明

**更新时间**: 2025-12-21
**API地址**: https://google-api.aihang365.com

---

## 新增模型

### 1. gemini-3-pro-image-preview-2k

**特点**:
- 基于 Gemini 3.0 Pro
- 2K分辨率 (2048x2048)
- 高质量图片生成
- 适合日常使用

**API调用**:
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview-2k",
    "prompt": "A cute orange cat sitting on a wooden table",
    "n": 1,
    "size": "1024x1024"
  }'
```

**预期性能**:
- 生成时间: ~60秒
- 图片尺寸: 2048x2048px
- 文件大小: ~2-3MB

---

### 2. gemini-3-pro-image-preview-4k

**特点**:
- 基于 Gemini 3.0 Pro
- 4K超高清 (4096x4096)
- 最高质量图片生成
- 适合专业用途

**API调用**:
```bash
curl -X POST https://google-api.aihang365.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview-4k",
    "prompt": "A cute orange cat sitting on a wooden table",
    "n": 1,
    "size": "1024x1024"
  }'
```

**预期性能**:
- 生成时间: ~80-120秒
- 图片尺寸: 4096x4096px
- 文件大小: ~8-12MB

---

## 所有可用图片生成模型对比

| 模型 | 分辨率 | 速度 | 质量 | 文件大小 | 推荐用途 |
|------|--------|------|------|---------|---------|
| gemini-3-pro-image-preview-4k | 4096x4096 | 慢 (~80-120s) | ⭐⭐⭐⭐⭐ | ~8-12MB | 专业设计、高质量需求 |
| gemini-3-pro-image-preview-2k | 2048x2048 | 中 (~60s) | ⭐⭐⭐⭐ | ~2-3MB | 日常使用、高质量需求 |
| gemini-3-pro-image-preview | 2048x2048 | 中 (~60s) | ⭐⭐⭐⭐ | ~1.4MB | 标准高质量生成 |
| gemini-2.5-flash-image | 2048x2048 | 快 (~30s) | ⭐⭐⭐ | ~1.4MB | 快速生成 |

---

## 技术实现

### 模型映射 (MODEL_MAP)

```python
MODEL_MAP = {
    # 图片模型 (Imagen)
    "gemini-2.5-flash-image": "IMAGEN_3_FAST",
    "gemini-3-pro-image-preview": "IMAGEN_3",
    "gemini-3-pro-image-preview-4k": "G_3_0_PRO",  # 4K高清
    "gemini-3-pro-image-preview-2k": "G_3_0_PRO",  # 2K
}
```

### 动态尺寸控制

```python
# 根据模型确定图片尺寸
image_size = "2048"  # 默认2K
if "4k" in request.model.lower():
    image_size = "4096"  # 4K高清
elif "2k" in request.model.lower():
    image_size = "2048"  # 2K

# 下载图片时使用动态尺寸
img_url = img.url + f'=s{image_size}'
```

---

## 限流规则

新增模型遵循相同的限流规则:

- **全局限流**: 每小时60次请求
- **模型限流**: 同一模型5秒间隔
- **独立限流**: 不同模型的限流是独立的

例如:
```
gemini-3-pro-image-preview-2k (第1次) → ✅ 成功
gemini-3-pro-image-preview-2k (第2次，立即) → ❌ 拒绝（需等5秒）
gemini-3-pro-image-preview-4k (立即) → ✅ 成功（不同模型）
```

---

## 使用建议

### 选择模型的建议

1. **快速原型/预览** → `gemini-2.5-flash-image`
   - 生成速度最快
   - 质量足够日常使用

2. **高质量内容** → `gemini-3-pro-image-preview-2k`
   - 平衡质量和速度
   - 适合大多数专业场景

3. **专业设计/打印** → `gemini-3-pro-image-preview-4k`
   - 最高分辨率
   - 适合需要超高清的场景

### 提示词优化

所有模型都会自动添加强化提示词:
```
Generate an actual image (not a description).
Create a visual representation of: {your_prompt}

IMPORTANT: You must generate an image, not text.
```

因此你的提示词应该:
- ✅ 直接描述画面内容
- ✅ 包含风格、光线、构图等细节
- ❌ 不需要说"生成一张图片"

**示例**:
```json
{
  "prompt": "A serene mountain landscape at sunset, snow-capped peaks, golden hour lighting, photorealistic style"
}
```

---

## 错误处理

### Cookie过期

**错误信息**:
```json
{
  "detail": "Failed to initialize client. SECURE_1PSIDTS could get expired frequently..."
}
```

**解决方法**:
1. 使用美国IP获取新的cookie
2. 更新服务器 `.env` 文件
3. 重启服务: `docker restart google-reverse`

### 限流错误

**错误信息**:
```json
{
  "detail": "模型 gemini-3-pro-image-preview-4k 调用过于频繁，请等待 4.2 秒后重试"
}
```

**解决方法**:
- 等待提示的秒数后重试
- 或切换到其他模型（不同模型限流独立）

---

## 部署记录

**Git提交**: 未提交（api_server.py不在仓库中）

**修改内容**:
1. 更新 `MODEL_MAP` 添加两个新模型
2. 添加动态尺寸控制逻辑
3. 保持限流规则不变

**服务器状态**:
```
✅ Gemini客户端初始化成功!
✅ Redis限流器初始化成功!
```

**测试状态**: ⚠️ 待Cookie更新后测试

---

## 下一步

1. ⚠️ 更新Cookie（当前已过期）
2. 🧪 测试两个新模型的实际生成效果
3. 📊 对比不同分辨率的图片质量
4. 📝 根据实际测试结果更新性能数据

---

**更新时间**: 2025-12-21 15:00
**状态**: ✅ 代码已部署，⚠️ 待Cookie更新后测试
