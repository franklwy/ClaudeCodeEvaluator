"""
Claude Code 会话日志解析器
"""
import json
import glob
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from ..models import (
    Message, MessageType, ToolUse, ToolType, 
    CodeOperation, SessionData
)
from ..config import CLAUDE_PROJECTS_DIR


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """解析ISO格式时间戳"""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def get_project_dir(project_path: str) -> Path:
    """获取项目对应的Claude日志目录"""
    # 将路径转换为Claude的目录名格式（用-替换/）
    dir_name = project_path.replace('/', '-')
    if dir_name.startswith('-'):
        dir_name = dir_name[1:]  # 去掉开头的-
    return CLAUDE_PROJECTS_DIR / f"-{dir_name}"


def find_session_files(project_path: str) -> List[Path]:
    """查找项目下所有会话文件"""
    project_dir = get_project_dir(project_path)
    if not project_dir.exists():
        # 尝试直接使用目录名
        project_dir = CLAUDE_PROJECTS_DIR / project_path
    
    if not project_dir.exists():
        return []
    
    # 排除 agent-*.jsonl 文件，只返回主会话文件
    return [
        f for f in project_dir.glob("*.jsonl")
        if not f.name.startswith("agent-")
    ]


def find_agent_files(project_dir: Path, session_id: str) -> List[Path]:
    """查找与指定session关联的agent文件"""
    agent_files = []
    for f in project_dir.glob("agent-*.jsonl"):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                first_line = fp.readline()
                if first_line:
                    data = json.loads(first_line)
                    if data.get('sessionId') == session_id:
                        agent_files.append(f)
        except (json.JSONDecodeError, IOError):
            continue
    return agent_files


def parse_tool_use(content_item: Dict[str, Any]) -> Optional[ToolUse]:
    """解析工具调用"""
    if content_item.get('type') != 'tool_use':
        return None
    
    name = content_item.get('name', '')
    tool_id = content_item.get('id', '')
    input_data = content_item.get('input', {})
    
    tool_use = ToolUse(
        name=name,
        tool_id=tool_id,
        input_data=input_data
    )
    
    # 提取文件路径和内容（针对 Write/Edit 操作）
    if name in ('Write', 'Edit', 'search_replace'):
        tool_use.file_path = input_data.get('file_path', '')
        tool_use.content = input_data.get('content', '') or input_data.get('new_string', '')
        if tool_use.content:
            tool_use.lines = len(tool_use.content.split('\n'))
    
    return tool_use


def parse_message_content(msg_data: Dict[str, Any]) -> Tuple[Optional[str], List[ToolUse], bool]:
    """
    解析消息内容
    返回: (文本内容, 工具调用列表, 是否为tool_result)
    """
    content = msg_data.get('content')
    tool_uses = []
    text_content = None
    is_tool_result = False
    
    if isinstance(content, str):
        text_content = content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                item_type = item.get('type', '')
                if item_type == 'text':
                    texts.append(item.get('text', ''))
                elif item_type == 'thinking':
                    pass  # 忽略thinking内容
                elif item_type == 'tool_use':
                    tool_use = parse_tool_use(item)
                    if tool_use:
                        tool_uses.append(tool_use)
                elif item_type == 'tool_result':
                    is_tool_result = True
                    texts.append(f"[tool_result: {str(item.get('content', ''))[:50]}]")
        text_content = '\n'.join(texts) if texts else None
    
    return text_content, tool_uses, is_tool_result


def parse_jsonl_file(file_path: Path) -> List[Dict[str, Any]]:
    """解析JSONL文件"""
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except IOError:
        return []
    return records


def parse_session_file(file_path: Path, include_agents: bool = True) -> SessionData:
    """
    解析单个会话文件
    
    Args:
        file_path: 会话文件路径
        include_agents: 是否包含关联的agent文件
    
    Returns:
        SessionData: 解析后的会话数据
    """
    session_id = file_path.stem
    project_dir = file_path.parent
    
    # 从目录名还原项目路径
    project_path = project_dir.name.replace('-', '/')
    if project_path.startswith('/'):
        project_path = project_path[1:]
    
    session = SessionData(
        session_id=session_id,
        project_path=project_path
    )
    
    # 解析主会话文件
    records = parse_jsonl_file(file_path)
    
    # 如果需要，也解析关联的agent文件
    if include_agents:
        agent_files = find_agent_files(project_dir, session_id)
        for agent_file in agent_files:
            records.extend(parse_jsonl_file(agent_file))
    
    # 转换为Message对象
    for record in records:
        rec_type = record.get('type', '')
        
        # 跳过非消息类型
        if rec_type in ('queue-operation', 'file-history-snapshot', 'summary'):
            continue
        
        if rec_type not in ('user', 'assistant'):
            continue
        
        msg_data = record.get('message', {})
        timestamp = parse_timestamp(record.get('timestamp'))
        
        if not timestamp:
            continue
        
        text_content, tool_uses, is_tool_result = parse_message_content(msg_data)
        
        msg = Message(
            uuid=record.get('uuid', ''),
            parent_uuid=record.get('parentUuid'),
            msg_type=MessageType.USER if rec_type == 'user' else MessageType.ASSISTANT,
            timestamp=timestamp,
            role=msg_data.get('role'),
            content=text_content,
            model=msg_data.get('model'),
            tool_uses=tool_uses,
            usage=msg_data.get('usage'),
            is_tool_result=is_tool_result,
            session_id=record.get('sessionId'),
            agent_id=record.get('agentId'),
            is_sidechain=record.get('isSidechain', False)
        )
        
        session.messages.append(msg)
        
        # 提取代码操作
        for tool_use in tool_uses:
            if tool_use.name in ('Write', 'Edit', 'search_replace') and tool_use.file_path:
                op = CodeOperation(
                    tool_type=ToolType[tool_use.name.upper()] if tool_use.name.upper() in ToolType.__members__ else ToolType.OTHER,
                    file_path=tool_use.file_path,
                    content=tool_use.content or '',
                    lines=tool_use.lines,
                    timestamp=timestamp
                )
                session.code_operations.append(op)
    
    # 按时间排序
    session.messages.sort(key=lambda m: m.timestamp)
    session.code_operations.sort(key=lambda o: o.timestamp)
    
    # 计算派生数据
    session.compute_derived_data()
    
    return session


def find_latest_session(project_path: Optional[str] = None) -> Optional[Path]:
    """
    查找最新的会话文件
    
    Args:
        project_path: 项目路径，如果为None则搜索所有项目
    
    Returns:
        最新会话文件的路径
    """
    if project_path:
        session_files = find_session_files(project_path)
    else:
        # 搜索所有项目
        session_files = []
        for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                session_files.extend([
                    f for f in project_dir.glob("*.jsonl")
                    if not f.name.startswith("agent-")
                ])
    
    if not session_files:
        return None
    
    # 按修改时间排序，返回最新的
    return max(session_files, key=lambda f: f.stat().st_mtime)


def list_sessions(project_path: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    列出会话
    
    Args:
        project_path: 项目路径
        limit: 返回数量限制
    
    Returns:
        会话信息列表
    """
    if project_path:
        session_files = find_session_files(project_path)
    else:
        session_files = []
        for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                session_files.extend([
                    f for f in project_dir.glob("*.jsonl")
                    if not f.name.startswith("agent-")
                ])
    
    # 按修改时间排序
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    sessions = []
    for f in session_files[:limit]:
        # 快速读取首条摘要
        summary = ""
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                for line in fp:
                    data = json.loads(line)
                    if data.get('type') == 'summary':
                        summary = data.get('summary', '')
                        break
                    elif data.get('type') == 'user':
                        content = data.get('message', {}).get('content', '')
                        if isinstance(content, str):
                            summary = content[:50]
                            break
        except:
            pass
        
        sessions.append({
            'session_id': f.stem,
            'project': f.parent.name,
            'modified': datetime.fromtimestamp(f.stat().st_mtime),
            'size': f.stat().st_size,
            'summary': summary
        })
    
    return sessions

