"""
Claude API 兼容层
让 Gemini Reverse API 支持 Claude Code CLI
"""

import json
import uuid
import time
from typing import Optional, List, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# Claude Code 核心系统提示词
CLAUDE_CODE_SYSTEM_PROMPT = """You are an interactive CLI tool that helps users with software engineering tasks.

IMPORTANT: Assist with authorized security testing, defensive security, CTF challenges, and educational contexts. Refuse requests for destructive techniques, DoS attacks, mass targeting, supply chain compromise, or detection evasion for malicious purposes.

IMPORTANT: You must NEVER generate or guess URLs for the user unless you are confident that the URLs are for helping the user with programming.

## Tone and style
- Only use emojis if the user explicitly requests it. Avoid using emojis in all communication unless asked.
- Your output will be displayed on a command line interface. Your responses should be short and concise.
- Output text to communicate with the user; all text you output outside of tool use is displayed to the user.
- NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.

## Professional objectivity
Prioritize technical accuracy and truthfulness over validating the user's beliefs. Focus on facts and problem-solving, providing direct, objective technical info without any unnecessary superlatives, praise, or emotional validation. Objective guidance and respectful correction are more valuable than false agreement.

## Task Management
Use TodoWrite tools to manage and plan tasks. Use these tools VERY frequently to ensure tracking tasks and giving visibility into progress. Mark todos as completed as soon as done with a task. Do not batch up multiple tasks before marking them as completed.

## Doing tasks
The user will primarily request software engineering tasks: solving bugs, adding new functionality, refactoring code, explaining code.
- NEVER propose changes to code you haven't read. Read files first before suggesting modifications.
- Be careful not to introduce security vulnerabilities: command injection, XSS, SQL injection, OWASP top 10.
- Avoid over-engineering. Only make changes directly requested or clearly necessary. Keep solutions simple and focused.
- Don't add features, refactor code, or make "improvements" beyond what was asked.
- Don't add docstrings, comments, or type annotations to code you didn't change.
- Avoid backwards-compatibility hacks. If something is unused, delete it completely.

## Tool usage policy
- When doing file search, prefer to use the Task tool to reduce context usage.
- You can call multiple tools in a single response. If no dependencies between them, make all independent tool calls in parallel.
- Use specialized tools instead of bash commands when possible: Read for reading files, Edit for editing, Write for creating files.

## Code References
When referencing specific functions or pieces of code include the pattern `file_path:line_number` to allow easy navigation.

## Git Safety Protocol
- NEVER update the git config
- NEVER run destructive git commands (push --force, hard reset) unless explicitly requested
- NEVER skip hooks (--no-verify) unless explicitly requested
- NEVER commit changes unless the user explicitly asks

Answer the user's request using the relevant tools if available. Check that all required parameters for each tool call are provided or can reasonably be inferred from context."""

# Claude Code 专用模型映射
CLAUDE_MODEL_MAP = {
    # Claude Code 专用模型 (-cc 后缀)
    "gemini-3-flash-preview-cc": "gemini-3-flash-preview",  # Haiku
    "gemini-3-pro-cc": "gemini-3.0-pro",                    # Sonnet/Opus

    # 也支持直接使用 Claude 模型名（映射到 Gemini）
    "claude-3-haiku-20240307": "gemini-3-flash-preview",
    "claude-3-sonnet-20240229": "gemini-3.0-pro",
    "claude-3-opus-20240229": "gemini-3.0-pro",
    "claude-3-5-sonnet-20240620": "gemini-3.0-pro",
    "claude-3-5-sonnet-20241022": "gemini-3.0-pro",
    "claude-sonnet-4-20250514": "gemini-3.0-pro",
    "claude-opus-4-5-20251101": "gemini-3.0-pro",
}

class ClaudeMessage(BaseModel):
    role: str
    content: Any  # str 或 List[dict]

class ClaudeMessagesRequest(BaseModel):
    model: str
    max_tokens: int = 4096
    messages: List[ClaudeMessage]
    stream: bool = False
    system: Optional[Any] = None  # 支持 str 或 List[dict] 格式
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None  # Claude Code 可能发送的额外字段

def extract_system_text(system: Any) -> str:
    """从 system 字段提取文本，支持字符串或数组格式"""
    if system is None:
        return ""
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        text_parts = []
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "\n".join(text_parts)
    return str(system)

def convert_claude_to_gemini_messages(messages: List[ClaudeMessage], system: Any = None, inject_claude_code_prompt: bool = True) -> str:
    """将 Claude 消息格式转换为 Gemini prompt"""
    parts = []

    # 注入 Claude Code 系统提示词（伪装成 Claude Code）
    if inject_claude_code_prompt:
        parts.append(f"System: {CLAUDE_CODE_SYSTEM_PROMPT}\n")

    # 用户提供的 system 提示词
    system_text = extract_system_text(system)
    if system_text:
        parts.append(f"Additional Context: {system_text}\n")

    for msg in messages:
        role = msg.role
        content = msg.content

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        tool_id = block.get("tool_use_id", "")
                        result = block.get("content", "")
                        text_parts.append(f"[Tool Result {tool_id}]: {result}")
            text = "\n".join(text_parts)
        else:
            text = str(content)

        if role == "user":
            parts.append(f"User: {text}")
        elif role == "assistant":
            parts.append(f"Assistant: {text}")

    return "\n\n".join(parts)

def create_claude_response(
    text: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    stop_reason: str = "end_turn"
) -> Dict[str, Any]:
    """创建 Claude API 格式的响应"""
    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": text
            }
        ],
        "model": model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    }

async def stream_claude_response(
    text: str,
    model: str,
    input_tokens: int = 0
) -> AsyncGenerator[str, None]:
    """生成 Claude SSE 流式响应"""
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"

    # message_start
    yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': model, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': input_tokens, 'output_tokens': 0}}})}\n\n"

    # content_block_start
    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

    # content_block_delta - 分块发送文本
    chunk_size = 20
    output_tokens = 0
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        output_tokens += len(chunk.split())
        yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': chunk}})}\n\n"

    # content_block_stop
    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

    # message_delta
    yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': output_tokens}})}\n\n"

    # message_stop
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

def get_gemini_client():
    """获取 Gemini 客户端（从主模块导入）"""
    from api_server import gemini_client
    return gemini_client

@router.post("/v1/messages")
async def claude_messages(request: ClaudeMessagesRequest):
    """Claude API 兼容的 /v1/messages 端点"""
    gemini_client = get_gemini_client()

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 模型映射
    original_model = request.model
    gemini_model = CLAUDE_MODEL_MAP.get(request.model, "gemini-3.0-pro")

    # 转换消息格式
    prompt = convert_claude_to_gemini_messages(request.messages, request.system)

    # 如果有 tools，添加到 prompt 中
    if request.tools:
        tools_desc = "\n\nAvailable tools:\n"
        for tool in request.tools:
            tools_desc += f"- {tool.get('name')}: {tool.get('description', '')}\n"
        prompt = tools_desc + "\n\n" + prompt

    try:
        # 调用 Gemini
        from gemini_webapi.constants import Model

        # 根据映射选择模型
        model_enum = None
        if "flash" in gemini_model.lower():
            model_enum = Model.G_2_5_FLASH
        elif "pro" in gemini_model.lower():
            model_enum = Model.G_2_5_PRO

        if model_enum:
            response = await gemini_client.generate_content(prompt, model=model_enum)
        else:
            response = await gemini_client.generate_content(prompt)

        response_text = response.text or ""

        # 估算 token 数
        input_tokens = len(prompt.split())
        output_tokens = len(response_text.split())

        # 注意: gemini-webapi 不支持真流式，强制使用非流式响应
        # 避免 Claude Code 因等待超时而断连
        if request.stream:
            # 即使请求流式，也返回非流式响应（Claude Code 兼容）
            pass

        # 非流式响应
        return create_claude_response(
                text=response_text,
                model=original_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/models")
async def list_claude_models():
    """返回可用的 Claude 兼容模型列表"""
    models = []

    # Claude Code 专用模型
    cc_models = [
        {
            "id": "gemini-3-flash-preview-cc",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "gemini-reverse",
            "description": "Fast model for Claude Code (maps to gemini-3-flash-preview)"
        },
        {
            "id": "gemini-3-pro-cc",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "gemini-reverse",
            "description": "Pro model for Claude Code (maps to gemini-3.0-pro)"
        }
    ]

    # Claude 原生模型名（也支持）
    claude_models = [
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-sonnet-20241022",
        "claude-sonnet-4-20250514",
        "claude-opus-4-5-20251101"
    ]

    for model_id in claude_models:
        models.append({
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "gemini-reverse"
        })

    return {
        "object": "list",
        "data": cc_models + models
    }
