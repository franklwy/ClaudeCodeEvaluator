"""
维度7: 任务最终完成度评分器
"""
from ..models import SessionData
from .base import BaseEvaluator


class TaskCompletionEvaluator(BaseEvaluator):
    """
    任务最终完成度评分
    
    逻辑：
    - 由用户手动输入完成度百分比（0-100）
    - 如果用户未输入，默认为 100%
    
    公式：
    - score = input_percentage / 100.0
    """
    
    @property
    def name(self) -> str:
        return "任务最终完成度"
    
    def evaluate(self, session: SessionData) -> float:
        # 默认 100%
        completion_rate = self.config.get('completion_rate', 100.0)
        
        # 确保输入在 0-100 之间
        completion_rate = max(0.0, min(100.0, float(completion_rate)))
        
        self._raw_value = completion_rate
        self._detail = f"用户评分: {completion_rate:.0f}%"
        
        return completion_rate / 100.0

