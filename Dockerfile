FROM python:3.11-slim

WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir gemini-webapi fastapi uvicorn[standard] httpx redis

COPY api_server.py /app/
COPY model_rate_limiter.py /app/

# 复制Web界面
COPY web /app/web/

EXPOSE 8100

# 启动命令
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8100"]
