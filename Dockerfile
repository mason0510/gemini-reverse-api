FROM python:3.11-slim

WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx

# 复制Web界面
COPY web /app/web/

EXPOSE 8100

# 启动命令（需要提供api_server.py）
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8100"]
