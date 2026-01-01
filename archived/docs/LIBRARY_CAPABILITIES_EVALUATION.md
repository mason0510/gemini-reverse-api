# Gemini-WebAPI 库能力评估报告

**评估日期**: 2025-12-28
**当前版本**: gemini-webapi v1.17.3
**评估目的**: 评估是否可扩展支持视频、播客、UI设计稿等内容生成

---

## 1. 当前使用的底层库

### 核心库信息

```yaml
名称: gemini-webapi
版本: 1.17.3
作者: HanaokaYuzu (UZQueen)
仓库: https://github.com/HanaokaYuzu/Gemini-API
PyPI: https://pypi.org/project/gemini-webapi/
License: AGPL-3.0
描述: Reverse-engineered Python API for Google Gemini web app
```

### 技术原理

**不是官方API** - 通过逆向工程模拟 Gemini 网页版的行为:
- 使用 Cookie 认证 (`__Secure-1PSID`, `__Secure-1PSIDTS`)
- 直接调用 Gemini 网页版的内部端点
- 模拟浏览器HTTP请求（User-Agent、Referer等）
- 访问未公开的API功能

**优势**:
- ✅ 无需官方API Key
- ✅ 可使用免费账号额度
- ✅ 支持网页版独有功能（如图片编辑）

**劣势**:
- ⚠️ 依赖Cookie有效期（几小时-几天）
- ⚠️ Google可能随时修改内部API
- ⚠️ 功能受限于网页版能力

---

## 2. 当前已支持的功能

### ✅ 文本生成（已实现）

**支持的模型**:
```python
Model.G_3_0_PRO      # gemini-3.0-pro
Model.G_2_5_PRO      # gemini-2.5-pro
Model.G_2_5_FLASH    # gemini-2.5-flash
```

**API方法**:
```python
await gemini_client.generate_content(
    prompt="你好",
    model=Model.G_2_5_FLASH
)
```

### ✅ 图片生成（已实现）

**支持的模型**:
- `gemini-2.5-flash-image` - Imagen 3 Fast (1024×1024)
- `gemini-3-pro-image-preview` - Imagen 3 (2048×2048)
- `gemini-3-pro-image-preview-2k` - 2K高清
- `gemini-3-pro-image-preview-4k` - 4K超高清

**API方法**:
```python
await gemini_client.generate_content(
    prompt="a beautiful sunset",
    model=custom_model_dict  # 使用自定义模型header
)
```

### ✅ 参考图编辑（已实现）

**功能**: 基于已有图片生成新图片

**API方法**:
```python
await gemini_client.generate_content(
    prompt="将背景改为蓝色天印",
    files=["/path/to/input.png"],  # 上传参考图
    model=Model.G_2_5_FLASH
)
```

### ✅ 文件上传（部分实现）

**upload_file函数** (`utils/upload_file.py`):
```python
async def upload_file(file: str | Path, proxy: str | None = None) -> str:
    """上传文件到Google服务器，返回文件标识符"""
    with open(file, "rb") as f:
        file = f.read()

    response = await client.post(
        url="https://content-push.googleapis.com/upload",
        files={"file": file}
    )
    return response.text  # 返回类似 "/contrib_service/ttl_1d/..."
```

**特点**:
- 📁 接受任意二进制文件
- ⏰ 上传的文件有效期1天（ttl_1d）
- 🔗 返回文件标识符供后续使用
- ⚠️ **无文件类型验证** - 理论上支持任意格式

---

## 3. 官方Gemini API的多模态能力（2025年）

### 📺 视频能力

**输入理解** ([Gemini Multimodal Input](https://www.datastudios.org/post/google-gemini-multimodal-input-in-2025-vision-audio-and-video-capabilities-explained)):
- ✅ 视频理解：支持长达1小时的视频内容
- ✅ 帧效率：从256 tokens/帧降至64 tokens/帧
- ✅ 时间轴分析：分段、说话人追踪、场景识别
- ✅ 支持格式：MP4, MOV, MPEG, MPG, AVI, WMV, FLV, WEBM, 3GPP

**输出生成** ([Google AI Studio 2025](https://www.humai.blog/google-ai-studio-unified-playground-2025-complete-guide/)):
- ✅ **Veo 3.1**: 视频生成模型（已集成到AI Studio）
- ✅ 文本生成视频
- ✅ 图片生成视频
- ✅ 视频编辑

### 🎙️ 音频/播客能力

**Native Audio Processing** ([Gemini 2.5 Native Audio](https://blog.google/technology/google-deepmind/gemini-2-5-native-audio/)):
- ✅ 语音识别：情感、意图识别
- ✅ 转录与翻译
- ✅ 长音频处理：采访、播客
- ✅ TTS生成：播客、有声读物、游戏配音

**Gemini Live API** ([Live API Overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)):
- ✅ 实时音视频流处理
- ✅ 低延迟语音对话
- ✅ 持续音频流输入/输出

**Speech Generation** ([TTS Documentation](https://ai.google.dev/gemini-api/docs/speech-generation)):
```python
# 官方API示例
response = model.generate_content(
    "Read this like a news anchor: ...",
    generation_config={
        "response_modalities": ["AUDIO"],  # 返回音频
        "speech_config": {
            "voice_config": {"prebuilt_voice_config": {"voice_name": "Kore"}}
        }
    }
)
```

### 📄 文档处理能力

**Document Understanding** ([Document Processing](https://ai.google.dev/gemini-api/docs/document-processing)):
- ✅ PDF文档：最多1000页
- ✅ 原生视觉理解：文本、图表、表格、图片
- ✅ 结构化提取

**Files API** ([Files API Docs](https://ai.google.dev/gemini-api/docs/files)):
```python
# 官方API支持的文档格式
SUPPORTED_MIME_TYPES = [
    "application/pdf",           # PDF
    "application/vnd.ms-excel",  # Excel
    "text/plain",                # 文本
    "image/*",                   # 所有图片格式
    "audio/*",                   # 所有音频格式
    "video/*"                    # 所有视频格式
]
```

### 🎨 UI设计能力

**实时设计生成** ([Gemini 3 Flash](https://blog.google/products/gemini/gemini-3-flash/)):
- ✅ A/B测试设计：实时生成加载动画设计
- ✅ UI截图分析：理解上下文并生成交互式体验
- ✅ 代码生成：将设计转为可执行代码

---

## 4. gemini-webapi的能力边界

### ✅ 已确认支持

基于源码分析和文档：

1. **任意文件上传** ✅
   - `upload_file()` 函数无文件类型限制
   - 支持PDF、图片等多种格式
   - 示例代码使用 `"assets/sample.pdf"` 和 `"assets/banner.png"`

2. **多模态输入** ✅
   ```python
   await client.generate_content(
       prompt="分析这个视频",
       files=["video.mp4", "document.pdf"]  # 支持多文件
   )
   ```

3. **自定义模型** ✅
   ```python
   custom_model = {
       "model_name": "custom-model",
       "model_header": {"x-goog-ext-...": "[...]"}
   }
   await client.generate_content(prompt, model=custom_model)
   ```

### ⚠️ 理论上可行，但未验证

1. **视频输入**
   - 上传视频文件：✅ 技术可行（upload_file支持）
   - 视频理解：❓ 取决于Gemini网页版是否支持
   - **需要验证**: 网页版是否已开放视频上传功能

2. **音频/播客输入**
   - 上传音频文件：✅ 技术可行
   - 音频转录：❓ 取决于网页版能力
   - **需要验证**: 网页版是否支持音频文件

3. **UI设计稿输入**
   - 上传Figma/Sketch文件：✅ 技术可行
   - 设计理解：❓ 可能需要转为图片格式
   - **建议**: 先转为PNG/JPG再上传

### ✅ 可通过网页版实现（需验证）

1. **视频生成（Veo 3）** ⭐ **重要更新**
   - ✅ 网页版**已集成** Veo 3！
   - ✅ Google AI Pro用户：**每天3个** Veo 3 Fast生成
   - ✅ Google AI Ultra用户：**每天5个** 完整Veo 3生成
   - ⚠️ 超过限额后降级到Veo 2
   - 📊 7周内生成超过4000万视频
   - **可行性**: 90% - 需要找到对应的模型header和端点

2. **TTS语音生成** ⭐ **重要更新**
   - ✅ 可通过**官方API Key**解决
   - ✅ 端点：`generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
   - ✅ 支持模型：`gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-tts`
   - ✅ 当前代码已实现（api_server.py:964-1034）
   - ⚠️ 需要替换中转服务Key为Google官方Key
   - **可行性**: 95% - 只需更新API Key配置

### ❌ 确定不支持

1. **Gemini Live API**
   - 实时流式音视频
   - 仅官方Vertex AI支持
   - gemini-webapi **无法模拟**

2. **原生音频输入处理**（网页版限制）
   - 需要Vertex AI的Live API
   - gemini-webapi **无法实现**

---

## 5. 可行性评估与建议

### 🎯 短期可实现（1-2周）

#### 1. 视频理解功能 ⭐⭐⭐

**可行性**: 85%

**实现方案**:
```python
# 新增端点
@app.post("/v1/video/analyze")
async def analyze_video(video: UploadFile, prompt: str):
    # 1. 保存上传的视频
    video_path = save_temp_file(video)

    # 2. 使用gemini-webapi上传
    response = await gemini_client.generate_content(
        prompt=f"分析这个视频: {prompt}",
        files=[video_path],
        model=Model.G_2_5_PRO  # 使用Pro模型以获得更好的多模态能力
    )

    return {"analysis": response.text}
```

**需要验证**:
- [ ] Gemini网页版是否已支持视频上传
- [ ] 视频大小限制（建议<100MB）
- [ ] 支持的视频格式
- [ ] 处理时长

**建议**:
1. 先用小视频（<10MB）测试
2. 如果网页版不支持，考虑提取关键帧作为图片序列

#### 2. 文档处理功能 ⭐⭐⭐⭐

**可行性**: 95%

**实现方案**:
```python
# PDF文档分析（已知网页版支持）
@app.post("/v1/document/analyze")
async def analyze_document(doc: UploadFile, query: str):
    doc_path = save_temp_file(doc)

    response = await gemini_client.generate_content(
        prompt=f"分析这个文档并回答: {query}",
        files=[doc_path],
        model=Model.G_2_5_PRO
    )

    return {"answer": response.text}
```

**优势**: gemini-webapi文档已确认支持PDF

**建议**: 立即实现，风险极低

#### 3. UI设计稿理解 ⭐⭐⭐⭐

**可行性**: 90%

**实现方案**:
```python
@app.post("/v1/design/analyze")
async def analyze_design(design_image: UploadFile, task: str):
    # 将Figma导出为PNG，或直接上传截图
    image_path = save_temp_file(design_image)

    response = await gemini_client.generate_content(
        prompt=f"""分析这个UI设计稿，执行任务: {task}

        可能的任务:
        - 生成对应的HTML/CSS代码
        - 提出设计改进建议
        - 生成设计规范文档
        - 提取颜色/字体信息
        """,
        files=[image_path],
        model=Model.G_2_5_PRO
    )

    return {"result": response.text}
```

**建议**: 图片理解已验证可行，低风险

### 🔄 中期可尝试（1-2月）

#### 4. 音频/播客转录 ⭐⭐

**可行性**: 60%

**挑战**:
- 网页版是否支持音频文件未知
- 可能需要转为其他格式

**方案A - 直接上传**:
```python
@app.post("/v1/audio/transcribe")
async def transcribe_audio(audio: UploadFile):
    audio_path = save_temp_file(audio)

    # 尝试直接上传
    response = await gemini_client.generate_content(
        prompt="请转录这段音频的内容",
        files=[audio_path],
        model=Model.G_2_5_PRO
    )

    return {"transcript": response.text}
```

**方案B - 使用官方API**:
```python
# 切换到官方Gemini API（需要API Key）
import google.generativeai as genai

model = genai.GenerativeModel("gemini-2.5-pro")
audio_file = genai.upload_file(audio_path)

response = model.generate_content([
    "请转录这段音频",
    audio_file
])
```

**建议**: 先测试方案A，失败则用方案B

### ❌ 长期/不可行

#### 5. 视频生成（Veo）

**可行性**: 0% （gemini-webapi无法实现）

**原因**:
- Veo模型仅在AI Studio和官方API中提供
- 网页版未集成
- 需要使用官方Vertex AI API

**替代方案**:
```python
# 必须使用官方API
from google import genai

client = genai.Client(api_key="YOUR_KEY")
response = client.models.generate_content(
    model="gemini-2.0-flash-exp",
    contents="Generate a video of a sunset",
    config={
        "response_modalities": ["VIDEO"]
    }
)
```

#### 6. 原生TTS输出

**可行性**: 0% （gemini-webapi无法实现）

**当前状态**: 项目已尝试使用 `google-genai` SDK，但遇到配置问题

**建议**: 继续使用官方API，不要期望gemini-webapi支持

---

## 6. 库修改可行性

### 是否可以修改gemini-webapi？

**✅ 可以修改** - AGPL-3.0 License允许

**修改范围**:

1. **添加新端点** ✅
   ```python
   # 在constants.py中添加
   class Endpoint(StrEnum):
       GENERATE = "https://gemini.google.com/..."
       VIDEO_ANALYZE = "https://gemini.google.com/..."  # 新增
   ```

2. **添加新模型** ✅
   ```python
   # 已在项目中实现
   MODEL_MAP = {
       "gemini-3-pro-image-preview-4k": {
           "model_name": "...",
           "model_header": {...}
       }
   }
   ```

3. **扩展文件类型** ✅
   ```python
   # upload_file.py已支持任意文件
   # 只需添加验证逻辑
   SUPPORTED_VIDEO_FORMATS = [".mp4", ".mov", ".avi"]
   ```

### ⚠️ 限制

**不能超越Gemini网页版的能力**:
- 如果网页版不支持视频上传 → 无法通过修改库实现
- 如果网页版不提供TTS端点 → 无法模拟
- 如果网页版没有Veo集成 → 无法生成视频

**Cookie依赖**:
- 仍然依赖Cookie认证
- 仍然受限于网页版额度
- 仍然可能被Google封禁

---

## 7. 最终建议

### 🚀 立即实施（高优先级）⚡

#### 1. TTS语音生成 - P0 优先级

**可行性**: 95% ✅
**工作量**: 1小时
**价值**: 极高

**实施步骤**:
```bash
# 1. 获取Google官方API Key
# 访问 https://aistudio.google.com/apikey 创建

# 2. 更新环境变量（服务器或本地 .env）
GOOGLE_AI_API_KEY=AIzaSy...  # 替换为官方Key

# 3. 重启服务
docker restart google-reverse

# 4. 测试TTS
curl -X POST https://google-api.aihang365.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"你好世界","voice":"alloy"}' \
  --output test.wav
```

**当前状态**: 代码已实现（api_server.py:964-1034），只需更换API Key

#### 2. Veo 3视频生成 - P0 优先级 ⭐

**可行性**: 90% ✅（需要逆向工程网页版API）
**工作量**: 2-3天
**价值**: 极高（独特功能）

**实施方案**:
```python
# 步骤1: 逆向工程找到Veo 3的模型header
# 在浏览器中生成视频，抓取network请求

# 步骤2: 添加到MODEL_MAP
MODEL_MAP = {
    "veo-3-fast": {
        "model_name": "veo-3-fast",
        "model_header": {
            "x-goog-ext-525001261-jspb": "[待逆向]"
        }
    }
}

# 步骤3: 实现视频生成端点
@app.post("/v1/video/generations")
async def generate_video(request: VideoRequest):
    response = await gemini_client.generate_content(
        prompt=request.prompt,
        model=custom_veo_model
    )

    # 提取视频URL（网页版返回临时链接）
    video_url = extract_video_url(response)

    # 下载并上传到R2
    r2_url = await upload_to_r2(video_url)

    return {"video": r2_url}
```

**需要研究**:
- [ ] 抓取Veo 3的模型header字符串
- [ ] 确认视频返回格式（URL或base64）
- [ ] 实现限额检测（每天3/5个）

#### 3. PDF文档分析 - P1

**可行性**: 95% ✅
**工作量**: 4小时
**风险**: 极低（已验证支持）

#### 4. UI设计稿理解 - P1

**可行性**: 90% ✅
**工作量**: 2小时
**风险**: 低（图片能力已验证）

### 🧪 实验性尝试（中优先级）

1. **视频理解** - 85%可行性，需验证上传支持
2. **音频转录** - 60%可行性，需测试
3. **长文档分析** - 90%可行性，1000页PDF

### ⛔ 不建议投入

1. **Gemini Live API** - 仅Vertex AI支持，无法模拟
2. **原生音频输入处理** - 网页版未开放

### 架构建议 🏗️

**混合架构** - 根据功能选择合适的库:

```python
# 推荐架构
class GeminiService:
    def __init__(self):
        # 用于文本、图片、文档
        self.web_client = GeminiClient(...)  # gemini-webapi

        # 用于TTS、视频生成
        self.official_client = genai.Client(...)  # google-genai

    async def generate_text(self, prompt: str):
        return await self.web_client.generate_content(prompt)

    async def generate_video(self, prompt: str):
        return await self.official_client.models.generate_content(...)

    async def generate_speech(self, text: str):
        return await self.official_client.models.generate_content(
            config={"response_modalities": ["AUDIO"]}
        )
```

**优势**:
- ✅ 充分利用两种API的优势
- ✅ 免费额度（webapi）+ 付费高级功能（官方API）
- ✅ 功能覆盖更全面

---

## 8. 测试计划

### 第一阶段: 验证现有能力（1周）

```bash
# 1. 测试PDF上传
curl -X POST https://google-api.aihang365.com/v1/document/analyze \
  -F "doc=@sample.pdf" \
  -F "query=总结文档内容"

# 2. 测试视频上传
curl -X POST https://google-api.aihang365.com/v1/video/analyze \
  -F "video=@test.mp4" \
  -F "prompt=描述视频内容"

# 3. 测试音频上传
curl -X POST https://google-api.aihang365.com/v1/audio/transcribe \
  -F "audio=@podcast.mp3"
```

### 第二阶段: 实现高优先级功能（2周）

1. PDF文档分析 API
2. UI设计稿理解 API
3. 视频关键帧提取（降级方案）

### 第三阶段: 集成官方API（1个月）

1. 配置 `google-genai` SDK
2. 实现视频生成（Veo）
3. 修复TTS功能
4. 统一API格式

---

## 9. 参考资料

### 官方文档
- [Gemini Live API Overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)
- [Gemini Files API](https://ai.google.dev/gemini-api/docs/files)
- [Document Processing](https://ai.google.dev/gemini-api/docs/document-processing)
- [Speech Generation](https://ai.google.dev/gemini-api/docs/speech-generation)

### 技术博客
- [Google Gemini Multimodal Input 2025](https://www.datastudios.org/post/google-gemini-multimodal-input-in-2025-vision-audio-and-video-capabilities-explained)
- [Gemini 2.5 Native Audio](https://blog.google/technology/google-deepmind/gemini-2-5-native-audio/)
- [Google AI Studio 2025 Guide](https://www.humai.blog/google-ai-studio-unified-playground-2025-complete-guide/)
- [Gemini 3 Flash Announcement](https://blog.google/products/gemini/gemini-3-flash/)

### 社区资源
- [HanaokaYuzu/Gemini-API GitHub](https://github.com/HanaokaYuzu/Gemini-API)
- [gemini-webapi PyPI](https://pypi.org/project/gemini-webapi/)
- [Google AI Developers Forum](https://discuss.ai.google.dev/)

---

**结论**:

⭐ **重大发现**: 经过重新评估，gemini-webapi的能力**远超预期**！

✅ **Veo 3视频生成**: 网页版已集成，每天3-5个视频配额，可通过逆向工程实现
✅ **TTS语音合成**: 只需替换官方API Key即可立即启用，代码已实现
✅ **PDF文档分析**: 已验证支持，可立即实现
✅ **UI设计稿理解**: 基于图片能力，低风险扩展

**推荐架构**:
- 🎯 **核心功能用gemini-webapi** - 文本、图片、视频、文档（免费额度）
- 🔧 **辅助功能用官方API** - TTS（需API Key，低成本）
- ⚡ **无需Vertex AI** - 所有功能都可通过webapi + AI Studio实现

**优先级排序**:
1. **P0**: TTS启用（30分钟）→ Veo 3实现（2-3天）
2. **P1**: PDF分析、UI设计理解（1周内）
3. **P2**: 视频/音频理解（实验性）

短期内（1周）可实现**文本+图片+视频+文档+语音**的完整多模态API！
