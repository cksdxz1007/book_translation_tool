#!/bin/bash
# Flask翻译应用启动脚本 - 前台运行
# 使用uv包管理器管理虚拟环境和依赖

set -e

echo "=================================="
echo "Flask翻译应用启动脚本 (前台模式)"
echo "=================================="
echo ""

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: 未检测到uv包管理器"
    echo "请先安装 uv: https://docs.astral.sh/uv/"
    exit 1
fi

# 检查Python版本
echo "📋 系统信息:"
echo "  Python版本: $(python3 --version)"
echo "  uv版本: $(uv --version)"
echo ""

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
echo "🚀 启动Flask应用..."
echo "访问地址: http://localhost:5001"
echo "管理界面: http://localhost:5001/admin"
echo ""
echo "按 Ctrl+C 停止应用"
echo "=================================="
echo ""

# 启动Flask应用
cd "$(dirname "$0")"
exec uv run python app.py
