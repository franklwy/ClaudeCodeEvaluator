"""
维度1: 首次需求完成度评分器
"""
from ..models import SessionData
from .base import BaseEvaluator


class CompletionEvaluator(BaseEvaluator):
    """
    首次需求完成度评分
    
    逻辑：
    - 如果只有1轮提示词，则认为首次完成
    - 如果有多轮，检查第2轮是否包含"修改"类关键词
    - 包含修改关键词则首次未完成(0分)，否则首次完成(1分)
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
        
        # 检查第2轮是否包含修改关键词
        modify_keywords = self.config.get('modify_keywords', [
            '修改', 'bug', '错误', 'fix', 'change', '改', '不对', '问题', 'error', 'wrong'
        ])
        
        second_prompt = session.user_prompts[1]
        content = (second_prompt.content or '').lower()
        
        for keyword in modify_keywords:
            if keyword.lower() in content:
                self._raw_value = False
                self._detail = f"✗ 首次未完成（第2轮包含'{keyword}'）"
                return 0.0
        
        self._raw_value = True
        self._detail = "✓ 首次即完成（后续为新需求）"
        return 1.0

