#!/bin/bash
# 带日志记录的应用程序启动脚本

# 日志文件名（包含时间戳）
LOG_FILE="app_startup_$(date +%Y%m%d_%H%M%S).log"

# 检查是否在正确的环境中
expected_python="/opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/python"
current_python=$(which python)

if [ "$current_python" != "$expected_python" ]; then
    echo "❌ 错误: 必须在 books_venv 环境中运行" | tee -a "$LOG_FILE"
    echo "当前 Python: $current_python" | tee -a "$LOG_FILE"
    echo "期望 Python: $expected_python" | tee -a "$LOG_FILE"
    echo "请执行: conda activate books_venv" | tee -a "$LOG_FILE"
    exit 1
fi

echo "=== 应用程序启动日志记录 ===" | tee -a "$LOG_FILE"
echo "开始时间: $(date)" | tee -a "$LOG_FILE"
echo "日志文件: $LOG_FILE" | tee -a "$LOG_FILE"
echo "BabelDOC 版本: $(babeldoc --version)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 启动应用程序并同时记录日志
echo "启动 Flask 应用程序..." | tee -a "$LOG_FILE"
python start_app.py 2>&1 | tee -a "$LOG_FILE"

# 记录结束时间
echo "" | tee -a "$LOG_FILE"
echo "应用程序已停止" | tee -a "$LOG_FILE"
echo "结束时间: $(date)" | tee -a "$LOG_FILE"
echo "日志已保存到: $LOG_FILE" | tee -a "$LOG_FILE"