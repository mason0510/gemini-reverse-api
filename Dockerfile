FROM python:3.11-slim

WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir gemini-webapi fastapi uvicorn[standard] httpx redis google-genai tenacity

# 复制核心Python文件
COPY api_server_v4.py /app/api_server.py
COPY claude_compat.py /app/
COPY cookie_persistence.py /app/
COPY watermark_remover.py /app/
COPY model_rate_limiter.py /app/

# 复制Web界面
COPY web /app/web/

# 创建数据目录
RUN mkdir -p /app/data

EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
