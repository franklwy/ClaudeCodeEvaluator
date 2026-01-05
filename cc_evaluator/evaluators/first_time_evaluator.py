"""
维度2: 首次完成时间评分器
"""
import math
from ..models import SessionData
from .base import BaseEvaluator


class FirstTimeEvaluator(BaseEvaluator):
    """
    首次完成时间评分
    
    逻辑：
    - 计算第一个用户请求到第一个AI回复的时间差
    - 时间在阈值内满分，超过阈值则指数衰减
    
    公式：
    - time <= threshold: score = 1.0
    - time > threshold: score = exp(-decay_rate * (time - threshold))
    """
    
    @property
    def name(self) -> str:
        return "首次完成时间"
    
    def evaluate(self, session: SessionData) -> float:
        threshold = self.config.get('threshold', 5.0)
        decay_rate = self.config.get('decay_rate', 0.1)
        max_time = self.config.get('max_time', 60.0)
        
        if not session.first_user_ts or not session.first_assistant_ts:
            self._raw_value = None
            self._detail = "无法计算（缺少时间数据）"
            return 0.0
        
        time_diff = (session.first_assistant_ts - session.first_user_ts).total_seconds()
        self._raw_value = time_diff
        
        if time_diff <= 0:
            self._detail = f"异常值: {time_diff:.1f}s"
            return 0.0
        
        if time_diff <= threshold:
            score = 1.0
            self._detail = f"耗时 {time_diff:.1f}s ≤ {threshold}s（满分）"
        elif time_diff >= max_time:
            score = 0.0
            self._detail = f"耗时 {time_diff:.1f}s ≥ {max_time}s（超时）"
        else:
            score = math.exp(-decay_rate * (time_diff - threshold))
            self._detail = f"耗时 {time_diff:.1f}s（阈值 {threshold}s）"
        
        return max(0.0, min(1.0, score))

