"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"
    SNAPSHOT = "file-history-snapshot"
    QUEUE_OP = "queue-operation"


class ToolType(Enum):
    WRITE = "Write"
    EDIT = "Edit"
    SEARCH_REPLACE = "search_replace"
    BASH = "Bash"
    READ = "Read"
    OTHER = "other"


@dataclass
class ToolUse:
    """工具调用记录"""
    name: str
    tool_id: str
    input_data: Dict[str, Any]
    file_path: Optional[str] = None
    content: Optional[str] = None
    lines: int = 0


@dataclass
class Message:
    """消息记录"""
    uuid: str
    parent_uuid: Optional[str]
    msg_type: MessageType
    timestamp: datetime
    role: Optional[str] = None
    content: Optional[str] = None
    model: Optional[str] = None
    tool_uses: List[ToolUse] = field(default_factory=list)
    usage: Optional[Dict[str, int]] = None
    is_tool_result: bool = False
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    is_sidechain: bool = False


@dataclass
class CodeOperation:
    """代码操作记录"""
    tool_type: ToolType
    file_path: str
    content: str
    lines: int
    timestamp: datetime


@dataclass
class SessionData:
    """会话数据"""
    session_id: str
    project_path: str
    messages: List[Message] = field(default_factory=list)
    code_operations: List[CodeOperation] = field(default_factory=list)
    
    # 派生数据
    user_prompts: List[Message] = field(default_factory=list)
    assistant_responses: List[Message] = field(default_factory=list)
    first_user_ts: Optional[datetime] = None
    first_assistant_ts: Optional[datetime] = None
    total_lines: int = 0
    
    @staticmethod
    def _is_eval_prompt(content: Optional[str], keywords: List[str]) -> bool:
        """判断是否为评分相关的提示词"""
        if not content:
            return False
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    def compute_derived_data(self):
        """计算派生数据"""
        from .config import FILTER_KEYWORDS
        
        # 过滤真实用户提示词（排除 tool_result、warmup、sidechain、评分相关）
        self.user_prompts = [
            m for m in self.messages 
            if (m.msg_type == MessageType.USER and 
                not m.is_tool_result and 
                not m.is_sidechain and
                not (m.content and 'warmup' in m.content.lower()) and
                not self._is_eval_prompt(m.content, FILTER_KEYWORDS))
        ]
        
        # AI响应（排除 sidechain，只保留真实回复）
        # 修复：确保排除Agent warmup消息 (is_sidechain=True)
        self.assistant_responses = [
            m for m in self.messages 
            if m.msg_type == MessageType.ASSISTANT and not m.is_sidechain
        ]
        
        # 首次时间（基于真实用户提示词和真实AI回复）
        if self.user_prompts:
            self.first_user_ts = min(m.timestamp for m in self.user_prompts)
        if self.assistant_responses:
            self.first_assistant_ts = min(m.timestamp for m in self.assistant_responses)
        
        # 总代码行数
        self.total_lines = sum(op.lines for op in self.code_operations)


@dataclass
class EvaluationResult:
    """单个维度的评分结果"""
    name: str
    score: float
    weight: float
    raw_value: Any
    detail: str
    
    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class EvaluationReport:
    """完整评分报告"""
    session_id: str
    project_path: str
    timestamp: datetime
    results: List[EvaluationResult] = field(default_factory=list)
    total_score: float = 0.0
    
    def compute_total_score(self):
        """计算综合得分"""
        if not self.results:
            self.total_score = 0.0
            return
        
        total_weight = sum(r.weight for r in self.results)
        if total_weight == 0:
            self.total_score = 0.0
            return
        
        weighted_sum = sum(r.weighted_score for r in self.results)
        self.total_score = weighted_sum / total_weight

