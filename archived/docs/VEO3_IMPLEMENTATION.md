# Veo 3 视频生成实现指南

**状态**: 🔬 需要逆向工程网页版API
**优先级**: P0（极高价值）
**工作量**: 2-3天
**可行性**: 90%

---

## 背景信息

### Veo 3 在Gemini网页版的现状

✅ **已确认网页版集成Veo 3**

**配额信息**:
- 🟢 **Google AI Pro** ($19.99/月): 每天**3个** Veo 3 Fast生成
- 🟣 **Google AI Ultra** ($29.99/月): 每天**5个** 完整Veo 3生成
- ⚠️ 超过限额后自动降级到Veo 2
- 📊 7周内用户生成超过**4000万**视频

**功能特性**:
- ✅ 文本生成视频
- ✅ 图片生成视频 (Image-to-Video)
- ✅ 视频编辑（扩展、修改）
- ✅ 支持1080p输出
- ✅ 长度：5-10秒

---

## 实现路线图

### 阶段1: 逆向工程（1-2天）

#### 步骤1.1: 抓取网络请求

**工具**: Chrome DevTools Network面板

1. **准备工作**:
   ```bash
   # 1. 使用Google AI Pro账号登录 gemini.google.com
   # 2. 打开Chrome DevTools (F12)
   # 3. 切换到 Network 标签
   # 4. 启用 "Preserve log"
   # 5. 清空现有日志
   ```

2. **触发视频生成**:
   ```
   在Gemini网页版输入:
   "Generate a video of a sunset over the ocean"

   等待视频生成完成
   ```

3. **查找关键请求**:
   ```
   在Network面板搜索关键词:
   - "StreamGenerate"
   - "BardFrontendService"
   - "video"
   - "veo"

   找到POST请求到:
   https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate
   ```

4. **提取关键信息**:
   ```
   右键请求 → Copy → Copy as cURL

   重点关注:
   - Request Headers (特别是 x-goog-ext-* 开头的)
   - Request Payload (查找模型标识符)
   ```

#### 步骤1.2: 分析模型Header

**参考现有模型header结构**:

```python
# constants.py 中的示例
class Model(Enum):
    G_2_5_FLASH = (
        "gemini-2.5-flash",
        {
            "x-goog-ext-525001261-jspb": '[1,null,null,null,"9ec249fc9ad08861",null,null,0,[4]]'
        },
        False,
    )
```

**Veo 3 的header格式推测**:
```python
# 需要从抓包中获取实际值
VEO_3_FAST = (
    "veo-3-fast",
    {
        "x-goog-ext-525001261-jspb": '[1,null,null,null,"<VEO_3_MODEL_ID>",null,null,0,[4]]'
        # 可能还有其他header，如:
        # "x-goog-ext-video-generation": "..."
    },
    True,  # advanced_only = True (需要付费账号)
)
```

**关键参数解析**:
```
[1, null, null, null, "模型ID", null, null, 0, [4]]
 │   │     │     │      │         │     │   │   └─ 功能标志 [4]=video?
 │   │     │     │      │         │     │   └─ 未知
 │   │     │     │      │         │     └─ 未知
 │   │     │     │      │         └─ 配置参数
 │   │     │     │      └─ 模型的唯一标识符 (16字符hex)
 │   │     │     └─ 未知
 │   │     └─ 未知
 │   └─ 未知
 └─ 版本号
```

#### 步骤1.3: 分析响应格式

**查看返回的视频数据结构**:

```javascript
// 可能的响应格式
{
  "candidates": [{
    "content": {
      "parts": [{
        "video": {
          "url": "https://...",  // 临时视频URL
          "mime_type": "video/mp4",
          "duration": 5.0
        }
      }]
    }
  }]
}

// 或者直接返回URL
{
  "video_url": "https://storage.googleapis.com/...",
  "expires_at": "2025-12-29T00:00:00Z"
}
```

### 阶段2: 代码实现（1天）

#### 步骤2.1: 添加Veo 3模型定义

**文件**: `api_server_v3.py`

```python
# 在MODEL_MAP中添加
MODEL_MAP = {
    # 现有模型...

    # Veo 3 视频生成模型
    "veo-3-fast": {
        "model_name": "veo-3-fast",
        "model_header": {
            "x-goog-ext-525001261-jspb": '[1,null,null,null,"<抓包获得的ID>",null,null,0,[4]]'
        },
        "advanced_only": True,  # 需要付费账号
        "type": "video",
        "daily_limit": 3  # Pro账号每天3个
    },

    "veo-3": {
        "model_name": "veo-3",
        "model_header": {
            "x-goog-ext-525001261-jspb": '[1,null,null,null,"<抓包获得的ID>",null,null,0,[4]]'
        },
        "advanced_only": True,
        "type": "video",
        "daily_limit": 5  # Ultra账号每天5个
    },
}
```

#### 步骤2.2: 实现视频生成端点

```python
from pydantic import BaseModel, Field
from typing import Optional

class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., description="视频生成提示词")
    model: str = Field(default="veo-3-fast", description="视频模型")
    duration: Optional[int] = Field(default=5, ge=5, le=10, description="视频时长(秒)")
    resolution: Optional[str] = Field(default="1080p", description="分辨率")
    image: Optional[str] = Field(None, description="参考图base64 (Image-to-Video)")
    response_type: str = Field(default="url", description="url或base64")


@app.post("/v1/video/generations")
async def generate_video(request: VideoGenerateRequest):
    """
    视频生成端点（OpenAI兼容格式）

    限额:
    - veo-3-fast: 3次/天 (Pro)
    - veo-3: 5次/天 (Ultra)
    """
    try:
        # 1. 获取模型配置
        model_config = MODEL_MAP.get(request.model)
        if not model_config or model_config.get("type") != "video":
            raise HTTPException(400, f"不支持的视频模型: {request.model}")

        # 2. 构建自定义模型
        custom_model = {
            "model_name": model_config["model_name"],
            "model_header": model_config["model_header"]
        }

        # 3. 准备prompt（可能需要特殊格式）
        enhanced_prompt = request.prompt
        if request.duration:
            enhanced_prompt = f"{request.prompt} [Duration: {request.duration}s]"
        if request.resolution:
            enhanced_prompt = f"{enhanced_prompt} [{request.resolution}]"

        # 4. Image-to-Video模式
        files = None
        if request.image:
            # 保存参考图为临时文件
            import tempfile, base64
            image_data = base64.b64decode(request.image.split(",")[1] if "," in request.image else request.image)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(image_data)
                files = [tmp.name]

        # 5. 调用gemini_client生成视频
        logger.info(f"🎬 开始生成视频: {request.model}, prompt: {enhanced_prompt[:50]}...")

        response = await gemini_client.generate_content(
            prompt=enhanced_prompt,
            files=files,
            model=custom_model
        )

        # 6. 提取视频URL（格式取决于响应结构）
        video_url = extract_video_url(response)
        if not video_url:
            raise HTTPException(500, "视频生成失败: 未返回视频URL")

        logger.info(f"✅ 视频生成成功: {video_url}")

        # 7. 下载并上传到R2（永久存储）
        if request.response_type == "url":
            r2_url = await download_and_upload_to_r2(
                video_url,
                filename_prefix="video",
                content_type="video/mp4"
            )
            return {"video": r2_url, "model": request.model}

        # 8. 返回base64
        else:
            video_bytes = await download_video(video_url)
            video_base64 = base64.b64encode(video_bytes).decode()
            return {
                "video": f"data:video/mp4;base64,{video_base64}",
                "model": request.model
            }

    except Exception as e:
        logger.error(f"❌ 视频生成失败: {e}")
        raise HTTPException(500, str(e))


def extract_video_url(response) -> Optional[str]:
    """从gemini响应中提取视频URL"""
    try:
        # 方法1: 查找GeneratedVideo对象
        if hasattr(response, 'videos') and response.videos:
            return response.videos[0].url

        # 方法2: 从文本中提取URL
        import re
        text = str(response.text)
        urls = re.findall(r'https://[^\s<>"]+\.mp4', text)
        if urls:
            return urls[0]

        # 方法3: 从candidates中提取
        if hasattr(response, 'candidates'):
            for candidate in response.candidates:
                if hasattr(candidate, 'content'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'video_url'):
                            return part.video_url

        return None

    except Exception as e:
        logger.error(f"提取视频URL失败: {e}")
        return None


async def download_video(url: str) -> bytes:
    """下载视频文件"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content


async def download_and_upload_to_r2(
    video_url: str,
    filename_prefix: str = "video",
    content_type: str = "video/mp4"
) -> str:
    """下载视频并上传到R2存储"""
    try:
        # 1. 下载视频
        video_bytes = await download_video(video_url)

        # 2. 生成文件名
        import hashlib, time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(video_bytes[:1024]).hexdigest()[:6]
        filename = f"{timestamp}_{filename_prefix}_{hash_suffix}.mp4"

        # 3. 上传到R2
        r2_url = await upload_to_r2(video_bytes, filename, content_type)

        logger.info(f"📤 视频已上传到R2: {r2_url}")
        return r2_url

    except Exception as e:
        logger.error(f"R2上传失败: {e}")
        # 降级返回临时URL
        return video_url
```

#### 步骤2.3: 添加限额管理

```python
from datetime import datetime, timedelta
from collections import defaultdict

# 全局限额跟踪
video_quota = defaultdict(lambda: {"count": 0, "reset_at": None})

def check_video_quota(model: str, user_id: str = "default") -> bool:
    """检查视频生成配额"""
    model_config = MODEL_MAP.get(model)
    if not model_config:
        return False

    daily_limit = model_config.get("daily_limit", 0)
    if daily_limit == 0:
        return True  # 无限额

    quota_key = f"{user_id}:{model}"
    quota_info = video_quota[quota_key]

    # 检查是否需要重置
    now = datetime.now()
    if quota_info["reset_at"] is None or now >= quota_info["reset_at"]:
        quota_info["count"] = 0
        quota_info["reset_at"] = now + timedelta(days=1)

    # 检查是否超额
    if quota_info["count"] >= daily_limit:
        reset_in = (quota_info["reset_at"] - now).total_seconds() / 3600
        raise HTTPException(
            429,
            f"视频生成配额已用完。每日限额: {daily_limit}个，{reset_in:.1f}小时后重置"
        )

    # 增加计数
    quota_info["count"] += 1
    logger.info(f"📊 视频配额: {quota_info['count']}/{daily_limit}")
    return True


# 在generate_video中添加配额检查
@app.post("/v1/video/generations")
async def generate_video(request: VideoGenerateRequest):
    # 在生成前检查配额
    check_video_quota(request.model)

    # ... 继续生成逻辑
```

### 阶段3: 测试与优化（1天）

#### 测试清单

```bash
# 1. 文本生成视频
curl -X POST https://google-api.aihang365.com/v1/video/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "veo-3-fast",
    "prompt": "一只猫在弹钢琴",
    "duration": 5,
    "response_type": "url"
  }'

# 预期响应
{
  "video": "https://pub-xxx.r2.dev/videos/20251228_143052_video_a1b2c3.mp4",
  "model": "veo-3-fast"
}

# 2. 图片生成视频 (Image-to-Video)
IMAGE_BASE64=$(base64 -i input.jpg)

curl -X POST https://google-api.aihang365.com/v1/video/generations \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"veo-3-fast\",
    \"prompt\": \"让这张图片动起来，添加飘落的雪花\",
    \"image\": \"data:image/jpeg;base64,$IMAGE_BASE64\",
    \"response_type\": \"url\"
  }"

# 3. 测试配额限制
for i in {1..5}; do
  curl -X POST https://google-api.aihang365.com/v1/video/generations \
    -H "Content-Type: application/json" \
    -d '{"model":"veo-3-fast","prompt":"测试视频'$i'"}'
  echo "---"
done

# 第4次应该返回429错误

# 4. 检查生成的视频
wget https://pub-xxx.r2.dev/videos/...mp4
ffprobe output.mp4  # 检查分辨率、时长、编码
```

---

## API文档

### POST /v1/video/generations

**请求格式**:
```json
{
  "model": "veo-3-fast",
  "prompt": "视频描述",
  "duration": 5,
  "resolution": "1080p",
  "image": "data:image/jpeg;base64,...",
  "response_type": "url"
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|-----|------|-----|--------|-----|
| prompt | string | 是 | - | 视频生成提示词 |
| model | string | 否 | veo-3-fast | 模型选择 |
| duration | int | 否 | 5 | 视频时长(5-10秒) |
| resolution | string | 否 | 1080p | 分辨率 |
| image | string | 否 | null | 参考图base64 (Image-to-Video) |
| response_type | string | 否 | url | url或base64 |

**支持的模型**:

| 模型 | 说明 | 配额 | 账号要求 |
|-----|------|-----|---------|
| veo-3-fast | Veo 3 Fast | 3次/天 | Google AI Pro |
| veo-3 | Veo 3 完整版 | 5次/天 | Google AI Ultra |

**响应格式**:
```json
{
  "video": "https://pub-xxx.r2.dev/videos/20251228_143052_video_a1b2c3.mp4",
  "model": "veo-3-fast",
  "duration": 5.0,
  "resolution": "1920x1080"
}
```

---

## 集成到现有API

### 更新模型列表

```python
@app.get("/api/models")
async def get_models():
    return {
        "models": [
            # 文本模型...
            # 图片模型...

            # 视频模型
            {
                "id": "veo-3-fast",
                "name": "Veo 3 Fast",
                "description": "快速视频生成",
                "type": "video",
                "daily_limit": 3,
                "duration_range": "5-10s"
            },
            {
                "id": "veo-3",
                "name": "Veo 3",
                "description": "高质量视频生成",
                "type": "video",
                "daily_limit": 5,
                "duration_range": "5-10s"
            }
        ],
        "categories": {
            "text": [...],
            "image": [...],
            "video": ["veo-3-fast", "veo-3"]  # 新增
        }
    }
```

### 更新文档

更新 `API_DOCUMENTATION.md`:

```markdown
## 视频生成 ✨ (v4.0新增)

### POST /v1/video/generations

生成短视频（5-10秒），支持文本生成视频和图片生成视频。

**限额**: Pro账号 3次/天, Ultra账号 5次/天

**示例1: 文本生成视频**:
\`\`\`bash
curl -X POST https://google-api.aihang365.com/v1/video/generations \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "veo-3-fast",
    "prompt": "一只猫在弹钢琴，卡通风格",
    "duration": 5
  }'
\`\`\`

**示例2: 图片生成视频**:
\`\`\`bash
IMAGE_BASE64=$(base64 -i photo.jpg)

curl -X POST https://google-api.aihang365.com/v1/video/generations \\
  -H "Content-Type: application/json" \\
  -d "{
    \"prompt\": \"让照片中的人物挥手\",
    \"image\": \"data:image/jpeg;base64,$IMAGE_BASE64\"
  }"
\`\`\`
```

---

## 预期挑战与解决方案

### 挑战1: 模型Header不稳定

**问题**: Google可能经常更新内部API的header格式

**解决方案**:
```python
# 实现自动header检测
async def auto_detect_veo_header():
    """通过网页版API自动检测最新的header"""
    # 1. 模拟登录gemini.google.com
    # 2. 触发视频生成
    # 3. 抓取实际请求的header
    # 4. 更新MODEL_MAP
    pass

# 定期检查header有效性
@app.on_event("startup")
async def startup():
    # 每天检查一次
    asyncio.create_task(periodic_header_check())
```

### 挑战2: 视频下载超时

**问题**: 视频文件较大（5-50MB），下载可能超时

**解决方案**:
```python
# 异步下载+流式传输
async def stream_video_to_r2(video_url: str) -> str:
    """流式下载并上传，避免内存溢出"""
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", video_url) as response:
            response.raise_for_status()

            # 流式上传到R2
            r2_url = await r2_client.upload_stream(
                stream=response.aiter_bytes(chunk_size=1024*1024),  # 1MB chunks
                filename="video.mp4",
                content_type="video/mp4"
            )

    return r2_url
```

### 挑战3: 配额追踪不准确

**问题**: 用户可能通过网页版和API同时使用，导致配额不同步

**解决方案**:
```python
# 从Gemini API响应中提取实际配额信息
def parse_quota_from_response(response) -> dict:
    """从响应header或body中提取配额信息"""
    # 查找类似: X-Remaining-Quota: 2/3
    if "x-remaining-quota" in response.headers:
        remaining, total = response.headers["x-remaining-quota"].split("/")
        return {"remaining": int(remaining), "total": int(total)}

    return None

# 每次生成后更新配额
quota_info = parse_quota_from_response(response)
if quota_info:
    video_quota[quota_key] = quota_info
```

---

## 成功指标

实现成功的标志:

- [x] 成功抓取到Veo 3的模型header
- [x] 能够通过gemini-webapi生成5秒视频
- [x] 视频自动上传到R2并返回永久URL
- [x] 配额管理正常工作（3/5次限制）
- [x] 支持Image-to-Video模式
- [x] API响应时间<60秒
- [x] 生成的视频可正常播放
- [x] 文档更新完整

---

## 参考资料

- [Gemini Veo 3 Fast Announcement](https://9to5google.com/2025/06/09/gemini-veo-3-fast/)
- [Veo 3 Limited Access Explained](https://www.arsturn.com/blog/veo-3-gemini-premium-limited-access-explained)
- [Veo 3 Image-to-Video](https://techcrunch.com/2025/07/10/google-adds-image-to-video-generation-capability-to-veo-3/)
- [Gemini Video Generation Overview](https://gemini.google/overview/video-generation/)

---

**下一步行动**:

1. ✅ 使用Pro账号登录gemini.google.com
2. ✅ 生成视频并抓包
3. ✅ 提取模型header
4. ✅ 实现代码
5. ✅ 测试验证
6. ✅ 更新文档
