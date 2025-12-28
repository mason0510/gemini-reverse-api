# Gemini-Web_API 逆向工程实现与架构设计

**来源**: CSDN博客 - 猫敷雪
**发布时间**: 2025-09-28
**阅读量**: 2.1k
**原文链接**: [CSDN文章](需要补充)

---

## 摘要

本文以逆向工程视角，对 Gemini-API（一个非官方的 Google Gemini 异步 Python 封装库）进行剖析。通过解析其核心架构设计、功能模块实现及关键技术难点，揭示逆向工程 API 封装的工程实践方法。研究表明，该库通过分层设计、异步机制与类型系统的结合，实现了对 Gemini 网页应用的高效调用，为大语言模型非官方 API 开发提供了可借鉴的技术范式。

---

## 1. 背景与研究意义

### 1.1 大语言模型 API 生态现状

随着生成式人工智能技术的快速发展，Google Gemini 作为主流大语言模型之一，其官方 API 存在访问限制、配额管控和功能权限等约束。根据 Google AI Studio 官方文档，免费用户存在每分钟请求次数限制（QPM）和每日令牌额度（TPD），这对需要高频调用或特定功能的开发者造成了阻碍。

非官方 API 封装作为补充方案，通过逆向工程网页应用接口，能够突破部分限制并提供更灵活的调用方式。`acheong08/Bard` 等先驱项目已验证了该技术路线的可行性，但针对 Gemini 的专业化封装仍存在技术空白。

### 1.2 Gemini-API 项目定位

**Gemini-API** 是一个逆向工程实现的异步 Python 库，旨在提供与官方 API 风格一致的 Gemini 网页应用调用接口。其核心价值在于：

- ✅ 实现无官方 API 密钥情况下的 Gemini 服务访问
- ✅ 支持官方 API 暂未开放的高级功能（如 Imagen4 图像生成）
- ✅ 提供比官方更灵活的会话管理与扩展能力

---

## 2. 系统架构与模块设计

### 2.1 整体架构 Overview

该项目采用分层设计思想，整体架构分为：

1. **核心客户端层**（GeminiClient）：处理认证与会话管理
2. **功能模块层**：实现具体业务能力（如 GemMixin 处理系统提示）
3. **数据类型层**：定义交互数据结构（如 Gem、ModelOutput）
4. **工具层**：提供网络请求、日志等基础设施

```
┌─────────────────────────────────────────┐
│            应用接口层                   │
│  (GeminiClient, ChatSession)            │
├─────────────────────────────────────────┤
│            功能模块层                   │
│  (GemMixin, 图像处理, 扩展支持)         │
├─────────────────────────────────────────┤
│            数据类型层                   │
│  (Gem, ModelOutput, Candidate)          │
├─────────────────────────────────────────┤
│            基础设施层                   │
│  (网络请求, 认证处理, 日志)             │
└─────────────────────────────────────────┘
```

---

### 2.2 核心模块详细分析

#### 2.2.1 客户端模块（`client`）

该模块实现了 `GeminiClient` 类，作为与 Gemini 服务交互的核心入口，主要职责包括：

**1. 认证管理**

- 支持通过 `__Secure-1PSID` 和 `__Secure-1PSIDTS` Cookie 认证
- 集成 `browser-cookie3` 实现浏览器 Cookie 自动导入
- 背景自动刷新 Cookie 机制（`start_auto_refresh` 方法）

```python
# 认证初始化关键代码
async def init(self, timeout: float = 300, ...):
    access_token, valid_cookies = await get_access_token(
        base_cookies=self.cookies, proxy=self.proxy, verbose=verbose
    )
    self.client = AsyncClient(
        http2=True,
        timeout=timeout,
        proxy=self.proxy,
        headers=Headers.GEMINI.value,
        cookies=valid_cookies,
        **self.kwargs,
    )
```

**2. 会话管理**

- 支持自动关闭闲置连接（`auto_close` 参数）
- 维护请求超时与重试机制（`@running` 装饰器）
- 处理多轮对话上下文（通过 `ChatSession` 类）

**3. 内容生成核心方法**

- `generate_content` 实现文本与文件输入的处理
- 支持模型选择、系统提示（Gem）应用等高级参数

---

#### 2.2.2 系统提示模块（`gem_mixin` 与 `gem`）

该模块实现了对 **Gemini Gems**（系统提示模板）的管理能力，包括：

**1. 数据结构定义**

- `Gem` 类封装系统提示的 ID、名称、描述等属性
- `GemJar` 类提供宝石集合的检索与过滤功能（支持按 ID、名称、类型筛选）

```python
# Gem 数据模型定义
class Gem(BaseModel):
    id: str
    name: str
    description: str | None = None
    prompt: str | None = None
    predefined: bool  # 标识是否为系统预定义
```

**2. 核心功能实现**

- 宝石获取（`fetch_gems`）：区分系统预定义与用户自定义宝石
- 宝石管理：创建（`create_gem`）、更新（`update_gem`）、删除（`delete_gem`）

**3. 使用场景**

支持在对话中应用特定系统提示，如代码助手、翻译专家等角色定义：

```python
# 应用系统提示示例
coding_partner = system_gems.get(id="coding-partner")
response = await client.generate_content(
    "解释 Python 列表推导式",
    gem=coding_partner,
)
```

---

#### 2.2.3 数据类型模块（`types/` 目录）

该模块定义了所有交互数据结构，采用 **Pydantic** 模型确保类型安全：

**1. 核心输出类型**

- `ModelOutput`：封装生成结果，包含文本（`text`）、图像（`images`）、思考过程（`thoughts`）等
- `Candidate`：表示模型生成的候选回复，支持多候选结果切换

**2. 媒体类型**

- `WebImage`：网页引用图像
- `GeneratedImage`：AI 生成图像，支持保存到本地

---

#### 2.2.4 扩展功能模块

实现了官方 API 尚未开放的高级功能：

**1. 图像生成（Imagen4）**

通过自然语言描述生成图像，支持结果保存

**2. 第三方扩展集成**

支持调用 Gmail、YouTube 等 Gemini 扩展：

```python
# 调用 Gmail 扩展示例
response = await client.generate_content(
    "@Gmail 查看我邮箱中的最新消息"
)
```

---

## 3. 关键技术难点与解决方案

### 3.1 认证机制逆向与维持

**难点**：Gemini 网页应用采用复杂的 Cookie 认证机制（`__Secure-1PSID` 和 `__Secure-1PSIDTS`），且令牌存在有效期限制。

**解决方案**：

- ✅ 实现 Cookie 自动刷新机制（`rotate_1psidts` 函数）
- ✅ 背景任务定期更新令牌（`start_auto_refresh` 方法）
- ✅ 支持多来源 Cookie 导入（手动输入与浏览器自动获取）

---

### 3.2 异步架构设计

**难点**：高频 API 调用场景下的性能优化与资源管理。

**解决方案**：

- ✅ 基于 `httpx.AsyncClient` 实现全异步网络请求
- ✅ 设计自动关闭闲置连接机制（`auto_close` + `close_delay`）
- ✅ 通过装饰器 `@running` 统一处理请求重试与状态检查

---

### 3.3 接口兼容性维护

**难点**：网页应用 API 非公开且可能随时变更，导致逆向工程实现不稳定。

**解决方案**：

- ✅ 封装底层 RPC 调用（`_batch_execute` 方法）
- ✅ 统一错误处理机制，定义专门的异常类（`AuthError`、`APIError` 等）
- ✅ 实现请求重试逻辑，提高鲁棒性

---

### 3.4 功能完整性实现

**难点**：复现网页应用的全部功能（如多轮对话、图像生成、扩展调用）。

**解决方案**：

- ✅ 设计 `ChatSession` 类维护对话上下文
- ✅ 解析并模拟网页端文件上传流程
- ✅ 逆向工程扩展调用协议，支持 `@` 指令语法

---

## 4. 安装与使用示例

### 4.1 环境准备

支持 Python 3.10+，通过 pip 安装：

```bash
# 基础安装
pip install -U gemini_webapi

# 可选：支持浏览器 Cookie 自动导入
pip install -U browser-cookie3
```

---

### 4.2 快速入门

#### Initialization（初始化）

```python
import asyncio
from gemini_webapi import GeminiClient

# 替换为实际的 Cookie 值
Secure_1PSID = "COOKIE VALUE HERE"
Secure_1PSIDTS = "COOKIE VALUE HERE"

async def main():
    # 如果安装了 browser-cookie3，可以直接使用 client = GeminiClient()
    client = GeminiClient(Secure_1PSID, Secure_1PSIDTS, proxy=None)
    await client.init(timeout=30, auto_close=False, close_delay=300, auto_refresh=True)

asyncio.run(main())
```

**参数说明**：

- `auto_close` 和 `close_delay` 是可选参数，用于在一定时间不活动后自动关闭客户端
- 对于长期运行的服务（如聊天机器人），建议设置 `auto_close=True` 并配置合理的 `close_delay` 秒数

---

#### Generate Contents（生成内容）

```python
async def main():
    response = await client.generate_content("Hello World!")
    print(response.text)

asyncio.run(main())
```

**提示**：直接使用 `print(response)` 也可以获得相同的文本输出。

---

#### Generate Contents with Files（带文件的内容生成）

Gemini 支持文件输入，包括图像和文档。可以通过 `files` 参数传递文件路径列表（`str` 或 `pathlib.Path`）：

```python
from pathlib import Path

async def main():
    response = await client.generate_content(
        "介绍这两个文件的内容，它们之间有什么联系？",
        files=["assets/sample.pdf", Path("assets/banner.png")],
    )
    print(response.text)

asyncio.run(main())
```

---

#### Conversations Across Multiple Turns（多轮对话）

如果需要保持连续对话，请使用 `GeminiClient.start_chat` 创建 `ChatSession` 对象。对话历史会自动维护和更新：

```python
async def main():
    chat = client.start_chat()
    response1 = await chat.send_message(
        "介绍这两个文件的内容，它们之间有什么联系？",
        files=["assets/sample.pdf", Path("assets/banner.png")],
    )
    print(response1.text)

    response2 = await chat.send_message(
        "使用图像生成工具修改这个banner，换一种字体和设计。"
    )
    print(response2.text, response2.images, sep="\n\n----------------------------------\n\n")

asyncio.run(main())
```

---

#### Continue Previous Conversations（继续之前的对话）

可以手动检索之前的对话，并在创建新的 `ChatSession` 时传递 `metadata`：

```python
async def main():
    # 开始新的对话
    chat = client.start_chat()
    response = await chat.send_message("今天天气不错")

    # 保存对话的元数据
    previous_session = chat.metadata

    # 加载之前的对话
    previous_chat = client.start_chat(metadata=previous_session)
    response = await previous_chat.send_message("我之前说了什么？")
    print(response)

asyncio.run(main())
```

---

#### Select Language Model（选择语言模型）

可以通过 `model` 参数指定使用哪个语言模型（默认为 `unspecified`）：

```python
from gemini_webapi.constants import Model

async def main():
    response1 = await client.generate_content(
        "你的语言模型版本是什么？只回复版本号。",
        model=Model.G_2_5_FLASH,
    )
    print(f"模型版本 ({Model.G_2_5_FLASH.model_name}): {response1.text}")

    chat = client.start_chat(model="gemini-2.5-pro")
    response2 = await chat.send_message("你的语言模型版本是什么？只回复版本号。")
    print(f"模型版本 (gemini-2.5-pro): {response2.text}")

asyncio.run(main())
```

**当前可用模型**（截至 2025-06-12）：

- `unspecified` - 默认模型
- `gemini-2.5-flash` - Gemini 2.5 Flash
- `gemini-2.5-pro` - Gemini 2.5 Pro（有每日使用限制）

**已弃用但仍可用的模型**：

- `gemini-2.0-flash` - Gemini 2.0 Flash
- `gemini-2.0-flash-thinking` - Gemini 2.0 Flash Thinking

---

#### Apply System Prompt with Gemini Gems（使用 Gemini Gems 应用系统提示）

系统提示可以通过 Gemini Gems 应用到对话中。可以传递 `gem` 参数（字符串 gem id 或 `Gem` 对象），每个对话只能应用一个 gem：

```python
async def main():
    # 获取所有 gems（包括系统预定义和用户创建的）
    await client.fetch_gems(include_hidden=False)

    # 获取后，gems 会被缓存在 `GeminiClient.gems` 中
    gems = client.gems

    # 获取想要使用的 gem
    system_gems = gems.filter(predefined=True)
    coding_partner = system_gems.get(id="coding-partner")

    response1 = await client.generate_content(
        "你的系统提示是什么？",
        model=Model.G_2_5_FLASH,
        gem=coding_partner,
    )
    print(response1.text)

    # 使用用户创建的自定义 gem
    your_gem = gems.get(name="Your Gem Name")
    your_gem_id = your_gem.id
    chat = client.start_chat(gem=your_gem_id)
    response2 = await chat.send_message("你的系统提示是什么？")
    print(response2)

asyncio.run(main())
```

**提示**：有些系统预定义的 gems 默认不会显示给用户（可能无法正常工作）。使用 `client.fetch_gems(include_hidden=True)` 可以在获取结果中包含它们。

---

#### Manage Custom Gems（管理自定义 Gems）

可以通过编程方式创建、更新和删除自定义 gems。注意：系统预定义的 gems 无法修改或删除。

**创建自定义 gem**：

```python
async def main():
    # 创建新的自定义 gem
    new_gem = await client.create_gem(
        name="Python Tutor",
        prompt="You are a helpful Python programming tutor.",
        description="A specialized gem for Python programming"
    )

    print(f"Custom gem created: {new_gem}")

    # 在对话中使用新创建的 gem
    response = await client.generate_content(
        "Explain how list comprehensions work in Python",
        gem=new_gem
    )
    print(response.text)

asyncio.run(main())
```

**更新现有 gem**：

更新 gem 时，必须提供所有参数（name、prompt、description），即使只想更改其中一个。

```python
async def main():
    # 获取自定义 gem
    await client.fetch_gems()
    python_tutor = client.gems.get(name="Python Tutor")

    # 使用新指令更新 gem
    updated_gem = await client.update_gem(
        gem=python_tutor,  # 也可以传递 gem ID 字符串
        name="Advanced Python Tutor",
        prompt="You are an expert Python programming tutor.",
        description="An advanced Python programming assistant"
    )

    print(f"Custom gem updated: {updated_gem}")

asyncio.run(main())
```

**删除自定义 gem**：

```python
async def main():
    # 获取要删除的 gem
    await client.fetch_gems()
    gem_to_delete = client.gems.get(name="Advanced Python Tutor")

    # 删除 gem
    await client.delete_gem(gem_to_delete)  # 也可以传递 gem ID 字符串
    print(f"Custom gem deleted: {gem_to_delete.name}")

asyncio.run(main())
```

---

#### Retrieve Model's Thought Process（获取模型的思考过程）

使用具有思考能力的模型时，模型的思考过程会填充在 `ModelOutput.thoughts` 中：

```python
async def main():
    response = await client.generate_content(
        "What's 1+1?", model="gemini-2.5-pro"
    )
    print(response.thoughts)
    print(response.text)

asyncio.run(main())
```

---

#### Retrieve Images in Response（获取响应中的图像）

API 输出中的图像以 `gemini_webapi.Image` 对象列表的形式存储。可以通过 `Image.title`、`Image.url` 和 `Image.alt` 访问图像标题、URL 和描述：

```python
async def main():
    response = await client.generate_content("Send me some pictures of cats")
    for image in response.images:
        print(image, "\n\n----------------------------------\n")

asyncio.run(main())
```

---

#### Generate Images with Imagen4（使用 Imagen4 生成图像）

可以通过自然语言要求 Gemini 使用 Imagen4（Google 最新的 AI 图像生成器）生成和修改图像。

**重要提示**：

Google 对 Gemini 中的图像生成功能有一些限制，因此该功能的可用性可能因地区/账户而异。以下是来自官方文档的摘要（截至 2025-03-19）：

- 该功能在任何特定 Gemini 应用中的可用性也受该应用支持的语言和国家/地区的限制
- 目前，18 岁以下的用户无法使用此功能
- 要使用此功能，必须登录 Gemini Apps

可以通过调用 `Image.save()` 将 Gemini 返回的图像保存到本地。可选地，可以通过传递 `path` 和 `filename` 参数指定文件路径和文件名，并通过传递 `skip_invalid_filename=True` 跳过具有无效文件名的图像。适用于 `WebImage` 和 `GeneratedImage`。

```python
async def main():
    response = await client.generate_content("Generate some pictures of cats")
    for i, image in enumerate(response.images):
        await image.save(path="temp/", filename=f"cat_{i}.png", verbose=True)
        print(image, "\n\n----------------------------------\n")

asyncio.run(main())
```

**注意**：

默认情况下，当要求发送图像时（如上例），Gemini 会发送从网络获取的图像，而不是使用 AI 模型生成图像，除非您在提示中明确要求"生成"图像。在此包中，网络图像和生成的图像被区别对待为 `WebImage` 和 `GeneratedImage`，并会在输出中自动分类。

---

#### Generate Contents with Gemini Extensions（使用 Gemini 扩展生成内容）

**重要提示**：

要在 API 中访问 Gemini 扩展，必须首先在 Gemini 网站上激活它们。与图像生成相同，Google 对 Gemini 扩展的可用性也有限制。以下是来自官方文档的摘要（截至 2025-03-19）：

- 要将应用连接到 Gemini，必须启用 Gemini Apps Activity
- 要使用此功能，必须登录 Gemini Apps
- 重要：如果您未满 18 岁，Google Workspace 和 Maps 应用目前仅适用于 Gemini 中的英语提示

为您的账户激活扩展后，可以通过自然语言或在提示开头使用"@"后跟扩展关键字来访问它们：

```python
async def main():
    response1 = await client.generate_content("@Gmail What's the latest message in my mailbox?")
    print(response1, "\n\n----------------------------------\n")

    response2 = await client.generate_content("@Youtube What's the latest activity of Taylor Swift?")
    print(response2, "\n\n----------------------------------\n")

asyncio.run(main())
```

**注意**：

对于可用地区限制，实际上只需要将您的 Google 账户的首选语言设置为上述三种支持的语言之一即可。您可以在[这里](https://myaccount.google.com/language)更改语言设置。

---

#### Check and Switch to Other Reply Candidates（检查和切换到其他回复候选）

Gemini 的响应有时包含多个具有不同生成内容的回复候选。您可以检查所有候选并选择一个继续对话。默认情况下，会选择第一个候选。

```python
async def main():
    # 开始对话并列出所有回复候选
    chat = client.start_chat()
    response = await chat.send_message("Recommend a science fiction book for me.")
    for candidate in response.candidates:
        print(candidate, "\n\n----------------------------------\n")

    if len(response.candidates) > 1:
        # 通过手动选择候选来控制正在进行的对话流程
        new_candidate = chat.choose_candidate(index=1)  # 在这里选择第二个候选
        followup_response = await chat.send_message("Tell me more about it.")  # 将基于所选候选生成内容
        print(new_candidate, followup_response, sep="\n\n----------------------------------\n\n")
    else:
        print("Only one candidate available.")

asyncio.run(main())
```

---

#### Logging Configuration（日志配置）

此包使用 `loguru` 进行日志记录，并公开了一个 `set_log_level` 函数来控制日志级别。可以将日志级别设置为以下值之一：`DEBUG`、`INFO`、`WARNING`、`ERROR` 和 `CRITICAL`。默认值为 `INFO`。

```python
from gemini_webapi import set_log_level

set_log_level("DEBUG")
```

---

## 5. 总结与展望

**Gemini-API** 通过模块化设计实现了对 Gemini 网页应用的高效封装，其技术亮点包括：

- ✅ **完善的类型系统**：基于 Pydantic 确保数据交互的类型安全
- ✅ **灵活的认证机制**：支持多种 Cookie 导入方式与自动刷新
- ✅ **丰富的功能覆盖**：实现官方 API 缺失的图像生成、扩展调用等功能
- ✅ **优雅的异步接口**：提供与官方 API 风格一致的异步编程体验

### 技术价值

1. **逆向工程方法论**：
   - 系统化的 Cookie 认证逆向方案
   - 网页 RPC 协议解析与封装
   - 异步架构下的资源管理策略

2. **工程实践参考**：
   - 分层架构设计（客户端层 → 功能层 → 数据层 → 基础设施层）
   - 类型安全保障（Pydantic 模型）
   - 自动化测试与文档（待补充）

3. **功能扩展性**：
   - 支持官方 API 未开放的 Imagen4 图像生成
   - 第三方扩展集成（Gmail、YouTube 等）
   - 自定义系统提示（Gems）管理

### 未来展望

1. **稳定性提升**：
   - 增强 Cookie 刷新机制的鲁棒性
   - 实现更完善的错误重试策略
   - 监控 Gemini 网页 API 变更并及时适配

2. **功能增强**：
   - 支持更多 Gemini 扩展（如 Google Drive、Calendar）
   - 实现流式响应（Streaming）
   - 添加批量请求优化

3. **生态建设**：
   - 完善文档和示例代码
   - 建立社区反馈机制
   - 提供 Docker 一键部署方案

---

## 附录：与本项目的关联

我们的 **Gemini Reverse API** 项目与上述 `gemini_webapi` 库在技术路线上高度一致，都采用了：

| 技术要点 | gemini_webapi | 我们的项目 |
|---------|--------------|-----------|
| **认证方式** | `__Secure-1PSID` + `__Secure-1PSIDTS` Cookie | ✅ 相同 |
| **异步架构** | `httpx.AsyncClient` | ✅ 类似（FastAPI + async） |
| **Cookie 自动刷新** | `start_auto_refresh` 方法 | ⚠️ 待实现 |
| **多轮对话** | `ChatSession` 类 | ✅ 已支持 |
| **图像生成** | Imagen4 集成 | ⚠️ 部分支持 |
| **系统提示** | Gems 管理 | ❌ 未实现 |

### 可借鉴的改进点

1. **Cookie 自动刷新机制**：
   - 参考 `rotate_1psidts` 函数实现
   - 添加后台任务定期更新 Cookie

2. **类型安全增强**：
   - 使用 Pydantic 定义所有数据模型
   - 严格的输入输出验证

3. **Gems 系统集成**：
   - 支持系统提示模板管理
   - 实现角色定制功能（如"代码助手"、"翻译专家"）

4. **错误处理优化**：
   - 定义专门的异常类（`AuthError`、`APIError`）
   - 实现统一的重试策略

---

**文档记录时间**: 2025-12-20
**记录者**: Claude Code
**项目路径**: `/Users/houzi/code/02-production/my-reverse-api/gemini-text/`
