"""
维度4: 总推理时间评分器
"""
from ..models import SessionData, MessageType
from .base import BaseEvaluator


class TotalTimeEvaluator(BaseEvaluator):
    """
    总推理时间评分
    
    逻辑：
    - 累加所有AI响应的时间（每个assistant消息与其前一条消息的时间差）
    - 时间越短分数越高
    
    公式：
    - score = max(0, 1 - total_time / max_time)
    """
    
    @property
    def name(self) -> str:
        return "总推理时间"
    
    def evaluate(self, session: SessionData) -> float:
        max_time = self.config.get('max_time', 60.0)
        
        if not session.messages:
            self._raw_value = 0
            self._detail = "无消息记录"
            return 0.0
        
        # 按时间排序的消息
        sorted_messages = sorted(session.messages, key=lambda m: m.timestamp)
        
        total_time = 0.0
        last_ts = None
        
        for msg in sorted_messages:
            if msg.msg_type == MessageType.ASSISTANT and last_ts:
                diff = (msg.timestamp - last_ts).total_seconds()
                # 只计算合理范围内的时间差
                if 0 < diff < 120:  # 单次响应不超过2分钟
                    total_time += diff
            last_ts = msg.timestamp
        
        self._raw_value = total_time
        
        if total_time <= 60:
            score = 1.0
            self._detail = f"总计 {total_time:.1f}s (≤1分钟, 满分)"
        else:
            minutes = total_time / 60.0
            score = 1.0 / minutes
            self._detail = f"总计 {total_time:.1f}s ({minutes:.1f}分钟, 得分1/{minutes:.1f})"
        
        return max(0.0, min(1.0, score))

