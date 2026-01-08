"""
维度5: 代码规模评分器
"""
from ..models import SessionData
from .base import BaseEvaluator


class CodeSizeEvaluator(BaseEvaluator):
    """
    代码规模评分
    
    逻辑：
    - 统计所有Write/Edit操作生成的代码总行数
    - 行数越少分数越高（在合理范围内）
    
    公式：
    - score = max(0, 1 - total_lines / max_lines)
    
    说明：
    - 这个维度的设计理念是：用更少的代码完成需求是更高效的
    - 但需要结合实际任务复杂度来解读
    """
    
    @property
    def name(self) -> str:
        return "代码规模"
    
    def evaluate(self, session: SessionData) -> float:
        total_lines = session.total_lines
        self._raw_value = total_lines
        
        if total_lines <= 0:
            self._detail = "无代码生成"
            return 1.0  # 没有生成代码，可能是纯问答
        
        # 新规则：分数 = 1 / 代码行数
        score = 1.0 / total_lines
        
        self._detail = f"生成 {total_lines} 行 (得分 1/{total_lines} = {score:.6f})"
        
        return score

