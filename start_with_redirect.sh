#!/bin/bash
# 简单的重定向日志记录脚本

# 日志文件名（包含时间戳）
LOG_FILE="app_output_$(date +%Y%m%d_%H%M%S).log"

# 检查是否在正确的环境中
expected_python="/opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/python"
current_python=$(which python)

if [ "$current_python" != "$expected_python" ]; then
    echo "❌ 错误: 必须在 books_venv 环境中运行"
    echo "当前 Python: $current_python"
    echo "期望 Python: $expected_python"
    echo "请执行: conda activate books_venv"
    exit 1
fi

echo "=== 应用程序启动（输出重定向到日志文件） ==="
echo "开始时间: $(date)"
echo "日志文件: $LOG_FILE"
echo ""
echo "启动应用程序... 所有输出将保存到 $LOG_FILE"
echo "按 Ctrl+C 停止应用程序"
echo ""

# 启动应用程序并将所有输出重定向到日志文件
/opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/python start_app.py > "$LOG_FILE" 2>&1

echo ""
echo "应用程序已停止"
echo "结束时间: $(date)"
echo "日志已保存到: $LOG_FILE"