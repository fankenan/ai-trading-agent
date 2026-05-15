# AI量化Agent - Dockerfile
# 多阶段构建，减小镜像体积

# 阶段1：构建前端
FROM node:18-alpine AS frontend-builder

WORKDIR /app/web-react
COPY web-react/package*.json ./
RUN npm ci --only=production

COPY web-react/ ./
RUN npm run build

# 阶段2：Python后端
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY data/ ./data/
COPY agent/ ./agent/
COPY run_multi_source.py .
COPY .env .

# 复制前端构建产物
COPY --from=frontend-builder /app/web-react/dist ./web-react/dist

# 暴露端口
EXPOSE 5002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5002/api/status || exit 1

# 启动命令
CMD ["python", "run_multi_source.py", "--host", "0.0.0.0", "--port", "5002"]
