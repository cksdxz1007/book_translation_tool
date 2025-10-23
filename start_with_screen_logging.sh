#!/bin/bash
# 使用 screen 记录完整会话的启动脚本

# 日志文件名（包含时间戳）
LOG_FILE="app_session_$(date +%Y%m%d_%H%M%S).log"
SESSION_NAME="book_translation_app_$(date +%Y%m%d_%H%M%S)"

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

echo "=== 使用 screen 记录应用程序会话 ==="
echo "会话名称: $SESSION_NAME"
echo "日志文件: $LOG_FILE"
echo "开始时间: $(date)"
echo ""
echo "启动 screen 会话并开始记录..."

# 启动 screen 会话并开始记录
screen -L -Logfile "$LOG_FILE" -S "$SESSION_NAME" -d -m /opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/python start_app.py

# 检查会话是否启动成功
if screen -list | grep -q "$SESSION_NAME"; then
    echo "✅ 应用程序已在 screen 会话中启动"
    echo "会话名称: $SESSION_NAME"
    echo "日志文件: $LOG_FILE"
    echo ""
    echo "📋 管理命令:"
    echo "  查看会话: screen -list"
    echo "  连接会话: screen -r $SESSION_NAME"
    echo "  停止会话: screen -X -S $SESSION_NAME quit"
    echo "  查看日志: tail -f $LOG_FILE"
    echo ""
    echo "💡 提示: 按 Ctrl+A 然后按 D 可以从会话中分离"
    echo "💡 提示: 按 Ctrl+C 可以停止应用程序"
else
    echo "❌ 启动 screen 会话失败"
    exit 1
fi