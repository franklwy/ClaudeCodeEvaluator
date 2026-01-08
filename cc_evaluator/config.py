"""
配置文件
"""
import os
from pathlib import Path

# Claude Code 日志目录
CLAUDE_PROJECTS_DIR = Path(os.path.expanduser("~/.claude/projects"))

# 评分时要过滤的提示词关键词（不计入统计）
FILTER_KEYWORDS = ['评分', '评估', '打分', 'score', 'evaluate', 'eval', 'cc-eval', '打个分']

# 评分参数配置
SCORING_CONFIG = {
    # 维度1: 首次需求完成度
    'first_completion': {
        'weight': 1.0,
        'modify_keywords': ['修改', 'bug', '错误', 'fix', 'change', '改', '不对', '问题', 'error', 'wrong']
    },
    
    # 维度2: 首次完成时间
    'first_time': {
        'weight': 1.0,
        'threshold': 5.0,      # 秒，低于此时间满分
        'decay_rate': 0.1,     # 指数衰减率
        'max_time': 60.0       # 超过此时间得0分
    },
    
    # 维度3: 提示词次数
    'prompt_count': {
        'weight': 1.0,
        'optimal': 1,          # 最优次数
        'max_count': 10        # 超过此次数得0分
    },
    
    # 维度4: 总推理时间
    'total_time': {
        'weight': 1.0,
        'max_time': 60.0       # 秒，超过此时间得0分
    },
    
    # 维度5: 代码规模
    'code_size': {
        'weight': 1.0,
        'max_lines': 500       # 超过此行数得0分
    }
}

# 支持的编程语言及其分析工具
LANGUAGE_CONFIG = {
    '.py': {
        'name': 'Python',
        'complexity_tool': 'radon',
        'lint_tool': 'flake8'
    },
    '.js': {
        'name': 'JavaScript',
        'complexity_tool': 'eslint',
        'lint_tool': 'eslint'
    },
    '.ts': {
        'name': 'TypeScript',
        'complexity_tool': 'eslint',
        'lint_tool': 'eslint'
    },
    '.java': {
        'name': 'Java',
        'complexity_tool': None,
        'lint_tool': None
    }
}

# 输出格式
OUTPUT_FORMATS = ['table', 'json', 'markdown']
DEFAULT_OUTPUT_FORMAT = 'table'

