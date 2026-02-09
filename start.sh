#!/bin/bash

echo "====================================="
echo "  电网母线负荷预测系统"
echo "  Grid Forecast System V9.2"
echo "====================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

echo "🚀 启动系统..."
python3 main.py
