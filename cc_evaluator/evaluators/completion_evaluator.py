"""
维度1: 首次需求完成度评分器
"""
from ..models import SessionData
from .base import BaseEvaluator


class CompletionEvaluator(BaseEvaluator):
    """
    首次需求完成度评分
    
    逻辑：
    - 如果只有1轮提示词，则认为首次完成（1分）
    - 如果有多轮提示词（>1），则认为首次未完成（0分）
    """
    
    @property
    def name(self) -> str:
        return "首次需求完成度"
    
    def evaluate(self, session: SessionData) -> float:
        prompt_count = len(session.user_prompts)
        
        if prompt_count <= 1:
            self._raw_value = True
            self._detail = "✓ 首次即完成（单轮对话）"
            return 1.0
        else:
            self._raw_value = False
            self._detail = f"✗ 首次未完成（共 {prompt_count} 轮对话）"
            return 0.0
