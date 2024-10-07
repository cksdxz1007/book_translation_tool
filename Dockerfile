# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器的 /app 中
COPY . /app

# 安装所需的包
RUN pip install --no-cache-dir -r requirements.txt

# 创建上传和结果文件夹
RUN mkdir -p uploads results

# 使端口 5000 可供此容器使用
EXPOSE 5000

# 定义环境变量
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# 运行 app.py
CMD ["flask", "run"]