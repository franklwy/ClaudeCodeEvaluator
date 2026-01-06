"""
维度3: 提示词次数评分器
"""
from ..models import SessionData
from .base import BaseEvaluator


class PromptCountEvaluator(BaseEvaluator):
    """
    提示词次数评分
    
    逻辑：
    - 统计真实用户提示词数量（排除tool_result）
    - 次数越少分数越高
    
    公式：
    - count <= optimal: score = 1.0
    - count > optimal: score = max(0, 1 - (count - optimal) / (max_count - optimal))
    """
    
    @property
    def name(self) -> str:
        return "提示词次数"
    
    def evaluate(self, session: SessionData) -> float:
        optimal = self.config.get('optimal', 1)
        max_count = self.config.get('max_count', 10)
        
        count = len(session.user_prompts)
        self._raw_value = count
        
        if count <= 0:
            self._detail = "无提示词"
            return 0.0
        
        if count <= 1:
            score = 1.0
            self._detail = f"共 {count} 次提示"
        else:
            score = 1.0 / count
            self._detail = f"共 {count} 次提示 (得分 1/{count})"
        
        return max(0.0, min(1.0, score))

