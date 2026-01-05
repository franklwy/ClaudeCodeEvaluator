"""
Claude Code 评分工具

用于评估 Claude Code 会话的执行效率和代码质量

使用方式:
    python -m cc_evaluator eval --latest
    python -m cc_evaluator list
    python -m cc_evaluator info <session_id>
"""
from .config import SCORING_CONFIG
from .models import SessionData, EvaluationResult, EvaluationReport
from .parser.session_parser import parse_session_file, find_latest_session, list_sessions
from .evaluators import ALL_EVALUATORS
from .reporter import ScoreReporter, generate_report
from .main import evaluate_session

__version__ = '1.0.0'
__author__ = 'Claude Code Evaluator'

__all__ = [
    'SCORING_CONFIG',
    'SessionData',
    'EvaluationResult',
    'EvaluationReport',
    'parse_session_file',
    'find_latest_session',
    'list_sessions',
    'ALL_EVALUATORS',
    'ScoreReporter',
    'generate_report',
    'evaluate_session',
]

