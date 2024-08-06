# 使用官方的Python 3.11基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件到工作目录
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install "python-telegram-bot[job-queue]"

# 暴露端口（如果需要）
# EXPOSE 8000

# 运行你的应用程序
CMD ["python", "main.py"]