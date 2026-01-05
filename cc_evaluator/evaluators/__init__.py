"""
评分模块
"""
from .base import BaseEvaluator
from .completion_evaluator import CompletionEvaluator
from .first_time_evaluator import FirstTimeEvaluator
from .prompt_count_evaluator import PromptCountEvaluator
from .total_time_evaluator import TotalTimeEvaluator
from .code_size_evaluator import CodeSizeEvaluator
from .code_quality_evaluator import CodeQualityEvaluator

# 所有评分器
ALL_EVALUATORS = [
    CompletionEvaluator,
    FirstTimeEvaluator,
    PromptCountEvaluator,
    TotalTimeEvaluator,
    CodeSizeEvaluator,
    CodeQualityEvaluator,
]

__all__ = [
    'BaseEvaluator',
    'CompletionEvaluator',
    'FirstTimeEvaluator',
    'PromptCountEvaluator',
    'TotalTimeEvaluator',
    'CodeSizeEvaluator',
    'CodeQualityEvaluator',
    'ALL_EVALUATORS',
]

