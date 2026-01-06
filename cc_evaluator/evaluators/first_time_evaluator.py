"""
维度2: 首次完成时间评分器
"""
from ..models import SessionData
from .base import BaseEvaluator


class FirstTimeEvaluator(BaseEvaluator):
    """
    首次完成时间评分
    
    逻辑：
    - 计算第一个用户请求到第一个AI回复的时间差
    - 时间越短分数越高
    
    公式：
    - time <= 60s: score = 1.0
    - time > 60s: score = 1 / (time / 60)
    """
    
    @property
    def name(self) -> str:
        return "首次完成时间"
    
    def evaluate(self, session: SessionData) -> float:
        if not session.first_user_ts or not session.first_assistant_ts:
            self._raw_value = None
            self._detail = "无法计算（缺少时间数据）"
            return 0.0
        
        time_diff = (session.first_assistant_ts - session.first_user_ts).total_seconds()
        self._raw_value = time_diff
        
        if time_diff <= 0:
            self._detail = f"异常值: {time_diff:.1f}s"
            return 0.0
        
        # 优化规则：1分钟内满分，超过1分钟倒数计分
        if time_diff <= 60:
            score = 1.0
            self._detail = f"耗时 {time_diff:.1f}s (≤1分钟, 满分)"
        else:
            minutes = time_diff / 60.0
            score = 1.0 / minutes
            self._detail = f"耗时 {time_diff:.1f}s ({minutes:.1f}分钟, 得分1/{minutes:.1f})"
        
        return max(0.0, min(1.0, score))
