#!/usr/bin/env python3
"""
Claude Code 评分工具 - MCP Server (FastMCP版)
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
LOG_FILE = Path(__file__).parent / "cc_eval.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger("mcp_server")

# --- Stdin Logger Start ---
class StdinLogger:
    """包装 stdin 以记录输入内容"""
    def __init__(self, original_stdin):
        self.original_stdin = original_stdin

    def read(self, size=-1):
        data = self.original_stdin.read(size)
        if data:
            logger.debug(f"STDIN READ: {data!r}")
        return data

    def readline(self, size=-1):
        line = self.original_stdin.readline(size)
        if line:
            logger.debug(f"STDIN READLINE: {line!r}")
        return line
    
    # 代理其他方法
    def __getattr__(self, name):
        return getattr(self.original_stdin, name)

# 替换 sys.stdin
sys.stdin = StdinLogger(sys.stdin)
logger.info("Stdin logger installed")
# --- Stdin Logger End ---

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("错误: 请先安装 mcp: pip install mcp", file=sys.stderr)
    sys.exit(1)

from cc_evaluator.config import CLAUDE_PROJECTS_DIR
from cc_evaluator.models import SessionData
from cc_evaluator.parser.session_parser import (
    parse_session_file,
    find_latest_session,
    list_sessions as core_list_sessions,
)
from cc_evaluator.main import evaluate_session as core_evaluate_session
from cc_evaluator.reporter import ScoreReporter, generate_report

# 创建 FastMCP 实例
mcp = FastMCP("cc-eval", dependencies=["mcp"])

# 添加启动日志
logger.info("MCP Server starting...")

@mcp.tool()
async def evaluate_session(
    action: str,
    session_id: str = "",
    project_path: str = "",
    include_agents: bool = False,
    first_completed: str = "auto",
    completion_rate: str = "",
    format: str = "table"
) -> str:
    """
    评估 Claude Code 会话的表现。
    
    必须提供 action 参数。
    
    Args:
        action: 必须固定输入 "eval"。
        session_id: 会话ID。如果不提供(留空)，默认评估【当前最新的】会话。
        project_path: 项目路径（可选）。
        include_agents: 是否包含agent文件（默认false）。
        first_completed: 首次请求是否完成需求 ("yes", "no", "auto")。默认 "auto"。
        completion_rate: 任务最终完成度 (0-100)。例如 "100" 或 "80"。留空表示默认100。
        format: 输出格式 (table, json, markdown)，默认 table。
    
    Returns:
        完整的评分报告表格。
    """
    logger.info(f"Tool Call: evaluate_session(action='{action}', session_id='{session_id}', format='{format}')")
    
    try:
        # 忽略 action 参数，它只是为了强制模型进行工具调用

        _session_id = session_id if session_id else None
        _project_path = project_path if project_path else None
        
        _first_completed = None
        if first_completed.lower() in ('yes', 'true', '1', 'y'):
            _first_completed = True
        elif first_completed.lower() in ('no', 'false', '0', 'n'):
            _first_completed = False
            
        _completion_rate = None
        if completion_rate:
            try:
                _completion_rate = float(completion_rate.replace('%', ''))
            except ValueError:
                pass

        # 确定会话文件
        session_file = None
        if _session_id:
            for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
                if project_dir.is_dir():
                    candidate = project_dir / f"{_session_id}.jsonl"
                    if candidate.exists():
                        session_file = candidate
                        break
            if not session_file:
                logger.warning(f"Session not found: {_session_id}")
                return f"错误: 找不到会话 {_session_id}"
        else:
            session_file = find_latest_session(_project_path)
            if not session_file:
                logger.warning("No session files found")
                return "错误: 找不到任何会话。请确保 Claude Code 已运行过至少一次。"

        logger.info(f"Target file: {session_file}")

        # 核心逻辑
        session = parse_session_file(session_file, include_agents=include_agents)
        
        # 确保是 SessionData 对象
        if not isinstance(session, SessionData):
            logger.error(f"parse_session_file returned unexpected type: {type(session)}")
            return "内部错误: 会话解析失败"

        results = core_evaluate_session(session, _first_completed, _completion_rate)
        report = generate_report(session, results)
        
        reporter = ScoreReporter(report, session)
        if format == "json":
            output = reporter.to_json()
        elif format == "markdown":
            output = reporter.to_markdown()
        else:
            output = reporter.to_table()
            
        logger.info(f"Evaluation successful, returning report of length {len(output)}")
        return output

    except Exception as e:
        logger.error(f"Error in evaluate_session: {e}", exc_info=True)
        return f"执行出错: {str(e)}"


@mcp.tool()
async def list_sessions(project_path: str = "", limit: int = 10) -> str:
    """
    列出历史会话记录。
    
    Args:
        project_path: 项目路径（可选）。
        limit: 返回数量限制（默认10）。
    """
    logger.info(f"Tool Call: list_sessions(limit={limit})")
    
    try:
        import inspect
        _project_path = project_path if project_path else None
        
        # 检查是否为协程（防御性编程）
        if inspect.iscoroutinefunction(core_list_sessions):
            sessions = await core_list_sessions(_project_path, limit)
        else:
            sessions = core_list_sessions(_project_path, limit)
            
        if not sessions:
            return "没有找到任何会话"

        lines = [f"找到 {len(sessions)} 个会话:\n"]
        lines.append(f"{'序号':<4} {'会话ID':<38} {'修改时间':<20} {'摘要':<30}")
        lines.append("-" * 100)
        
        for i, s in enumerate(sessions, 1):
            session_id = s['session_id'][:36]
            modified = s['modified'].strftime('%Y-%m-%d %H:%M:%S')
            summary = s['summary'][:30] if s['summary'] else "(无摘要)"
            lines.append(f"{i:<4} {session_id:<38} {modified:<20} {summary:<30}")
            
        return "\n".join(lines)


    except Exception as e:
        logger.error(f"Error in list_sessions: {e}", exc_info=True)
        return f"执行出错: {str(e)}"


@mcp.tool()
async def get_session_info(session_id: str) -> str:
    """
    获取指定会话的详细信息。
    
    Args:
        session_id: 会话ID (必需)
    """
    logger.info(f"Tool Call: get_session_info(session_id={session_id})")
    
    try:
        session_file = None
        for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                candidate = project_dir / f"{session_id}.jsonl"
                if candidate.exists():
                    session_file = candidate
                    break
        
        if not session_file:
            return f"错误: 找不到会话 {session_id}"

        session = parse_session_file(session_file)
        
        lines = [
            f"会话ID: {session.session_id}",
            f"项目: {session.project_path}",
            f"消息总数: {len(session.messages)}",
            f"AI回复: {len(session.assistant_responses)} 条",
        ]
        # ... (简化详情，保留核心)
        
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error in get_session_info: {e}", exc_info=True)
        return f"执行出错: {str(e)}"

if __name__ == "__main__":
    mcp.run()
