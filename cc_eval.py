#!/usr/bin/env python3
"""
Claude Code 评分工具 - 快捷启动脚本

使用方式:
    python cc_eval.py --latest              评估最新会话
    python cc_eval.py --session <id>        评估指定会话
    python cc_eval.py list                  列出所有会话
    python cc_eval.py info <session_id>     显示会话详情
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cc_evaluator.main import main

if __name__ == '__main__':
    main()

