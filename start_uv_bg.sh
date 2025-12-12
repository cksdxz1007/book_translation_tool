#!/bin/bash
# Flask翻译应用启动脚本 - 后台运行
# 使用uv包管理器管理虚拟环境和依赖

set -e

APP_NAME="flask-translation-app"
LOG_FILE="app.log"

echo "=================================="
echo "Flask翻译应用启动脚本 (后台模式)"
echo "=================================="
echo ""

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: 未检测到uv包管理器"
    echo "请先安装 uv: https://docs.astral.sh/uv/"
    exit 1
fi

# 检查是否已在运行
if pgrep -f "uv run python app.py" > /dev/null; then
    echo "⚠️  警告: 应用已在运行中"
    echo "PID: $(pgrep -f 'uv run python app.py')"
    echo "如需重启，请先停止现有进程"
    exit 1
fi

# 同步依赖
echo "📦 同步项目依赖..."
uv sync

# 检查.env文件
if [ ! -f .env ]; then
    echo "⚠️  警告: 未检测到 .env 文件"
    echo "正在从 .env.example 复制..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
    echo ""
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p uploads results data/keys
touch uploads/.gitkeep results/.gitkeep

# 生成加密密钥（如果不存在）
if [ ! -f data/keys/master.key ]; then
    echo "🔐 生成加密密钥..."
    python3 -c "from cryptography.fernet import Fernet; Fernet.generate_key().decode()" > data/keys/master.key
    chmod 600 data/keys/master.key
    echo "✅ 加密密钥已生成"
fi

echo ""
echo "🚀 启动Flask应用 (后台模式)..."
echo "应用名称: $APP_NAME"
echo "日志文件: $LOG_FILE"
echo "访问地址: http://localhost:5001"
echo "管理界面: http://localhost:5001/admin"
echo ""
echo "查看日志: tail -f $LOG_FILE"
echo "停止应用: ./stop_app.sh 或 pkill -f 'uv run python app.py'"
echo "=================================="
echo ""

# 启动后台进程
cd "$(dirname "$0")"
nohup uv run python app.py > "$LOG_FILE" 2>&1 &
APP_PID=$!

echo "✅ 应用已启动"
echo "PID: $APP_PID"
echo ""

# 等待几秒确保应用启动
sleep 3

# 检查应用是否成功启动
if ps -p $APP_PID > /dev/null; then
    echo "✅ 应用运行正常"
    echo "💡 提示: 使用以下命令管理应用"
    echo "  查看日志: tail -f $LOG_FILE"
    echo "  停止应用: kill $APP_PID"
else
    echo "❌ 应用启动失败，请检查日志: $LOG_FILE"
    exit 1
fi
