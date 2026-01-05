"""
评分器基类
"""
from abc import ABC, abstractmethod
from typing import Any

from ..models import SessionData, EvaluationResult


class BaseEvaluator(ABC):
    """评分器基类，所有评分维度必须继承此类"""
    
    def __init__(self, config: dict = None):
        """
        初始化评分器
        
        Args:
            config: 评分配置参数
        """
        self.config = config or {}
        self._raw_value = None
        self._detail = ""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """评分维度名称"""
        pass
    
    @property
    def weight(self) -> float:
        """权重，默认为1.0"""
        return self.config.get('weight', 1.0)
    
    @abstractmethod
    def evaluate(self, session: SessionData) -> float:
        """
        执行评分
        
        Args:
            session: 会话数据
        
        Returns:
            float: 0-1之间的分数
        """
        pass
    
    @property
    def raw_value(self) -> Any:
        """原始值（如时间、次数等）"""
        return self._raw_value
    
    @property
    def detail(self) -> str:
        """评分详情说明"""
        return self._detail
    
    def get_result(self, session: SessionData) -> EvaluationResult:
        """
        获取完整评分结果
        
        Args:
            session: 会话数据
        
        Returns:
            EvaluationResult: 评分结果
        """
        score = self.evaluate(session)
        return EvaluationResult(
            name=self.name,
            score=score,
            weight=self.weight,
            raw_value=self.raw_value,
            detail=self.detail
        )

