#!/usr/bin/env python3
"""
Claude Code 评分工具 - 主程序入口
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .config import SCORING_CONFIG, CLAUDE_PROJECTS_DIR
from .models import SessionData, EvaluationResult
from .parser.session_parser import (
    parse_session_file,
    find_latest_session,
    list_sessions,
    find_session_files
)
from .evaluators import (
    ALL_EVALUATORS,
    CompletionEvaluator,
    FirstTimeEvaluator,
    PromptCountEvaluator,
    TotalTimeEvaluator,
    CodeSizeEvaluator,
    TaskCompletionEvaluator,
)
from .reporter import ScoreReporter, generate_report


def evaluate_session(session: SessionData, first_completed: Optional[bool] = None, completion_rate: Optional[float] = None) -> List[EvaluationResult]:
    """
    对会话进行评分
    
    Args:
        session: 会话数据
        first_completed: 是否首次完成（可选，用于手动指定）
        completion_rate: 任务最终完成度（可选，0-100）
    
    Returns:
        评分结果列表
    """
    results = []
    
    # 1. 首次需求完成度
    completion_eval = CompletionEvaluator(SCORING_CONFIG.get('first_completion', {}))
    is_first_success = False  # 标记是否首次成功

    if first_completed is not None:
        # 手动指定
        completion_eval._raw_value = first_completed
        completion_eval._detail = "✓ 用户确认首次完成" if first_completed else "✗ 用户确认首次未完成"
        
        score = 1.0 if first_completed else 0.0
        is_first_success = bool(first_completed)
        
        results.append(EvaluationResult(
            name=completion_eval.name,
            score=score,
            weight=completion_eval.weight,
            raw_value=first_completed,
            detail=completion_eval._detail
        ))
    else:
        result = completion_eval.get_result(session)
        is_first_success = (result.score >= 1.0) # 如果得分是1.0，说明判定为成功
        results.append(result)
    
    # 2. 首次完成时间
    first_time_eval = FirstTimeEvaluator(SCORING_CONFIG.get('first_time', {}))
    
    # 如果首次未完成，首次时间强制为0分
    if not is_first_success:
        # 先获取原始结果以拿到时间数据
        temp_result = first_time_eval.get_result(session)
        
        # 覆盖分数
        first_time_eval._detail = f"{temp_result.detail} (但首次未完成，强制0分)"
        results.append(EvaluationResult(
            name=first_time_eval.name,
            score=0.0,
            weight=first_time_eval.weight,
            raw_value=temp_result.raw_value,
            detail=first_time_eval._detail
        ))
    else:
        results.append(first_time_eval.get_result(session))
    
    # 3. 提示词次数
    prompt_eval = PromptCountEvaluator(SCORING_CONFIG.get('prompt_count', {}))
    results.append(prompt_eval.get_result(session))
    
    # 4. 总推理时间
    total_time_eval = TotalTimeEvaluator(SCORING_CONFIG.get('total_time', {}))
    results.append(total_time_eval.get_result(session))
    
    # 5. 代码规模
    code_size_eval = CodeSizeEvaluator(SCORING_CONFIG.get('code_size', {}))
    results.append(code_size_eval.get_result(session))
    
    # 6. 任务最终完成度
    task_completion_eval = TaskCompletionEvaluator(SCORING_CONFIG.get('task_completion', {}))
    if completion_rate is not None:
        # 手动指定
        # 更新配置中的默认值，以便 evaluate 方法使用
        task_completion_eval.config['completion_rate'] = float(completion_rate)
    results.append(task_completion_eval.get_result(session))
    
    return results


def cmd_evaluate(args):
    """评估命令"""
    # 确定要评估的会话文件
    if args.session:
        # 指定会话ID
        session_file = None
        for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                candidate = project_dir / f"{args.session}.jsonl"
                if candidate.exists():
                    session_file = candidate
                    break
        
        if not session_file:
            print(f"错误: 找不到会话 {args.session}")
            sys.exit(1)
    elif args.latest:
        # 最新会话
        session_file = find_latest_session(args.project)
        if not session_file:
            print("错误: 找不到任何会话")
            sys.exit(1)
    elif args.file:
        # 指定文件
        session_file = Path(args.file)
        if not session_file.exists():
            print(f"错误: 文件不存在 {args.file}")
            sys.exit(1)
    else:
        print("错误: 请指定 --session, --latest 或 --file")
        sys.exit(1)
    
    if not args.quiet:
        print(f"正在解析会话: {session_file.name}")
    
    # 解析会话
    session = parse_session_file(session_file, include_agents=not args.no_agents)
    
    if not args.quiet:
        print(f"  - 用户提示词: {len(session.user_prompts)} 条")
        print(f"  - AI回复: {len(session.assistant_responses)} 条")
        print(f"  - 代码操作: {len(session.code_operations)} 个")
        print(f"  - 代码行数: {session.total_lines} 行")
        print()
    
    # 处理首次完成度
    first_completed = None
    completion_rate = None

    if args.first_completed:
        first_completed = args.first_completed.lower() in ('yes', 'true', '1', 'y')
    
    if args.completion_rate is not None:
        completion_rate = args.completion_rate

    if args.interactive:
        # 交互式询问首次完成
        if first_completed is None:
            print("请确认: 首次提示词是否完成了需求？")
            if session.user_prompts:
                print(f"  首次提示词: {session.user_prompts[0].content[:100] if session.user_prompts[0].content else '(空)'}")
            response = input("输入 y/n: ").strip().lower()
            first_completed = response in ('y', 'yes', '1')
        
        # 交互式询问最终完成度
        if completion_rate is None:
            print("\n请确认: 任务最终完成度是多少？(0-100)")
            try:
                rate_str = input("输入百分比(默认100): ").strip()
                completion_rate = float(rate_str) if rate_str else 100.0
            except ValueError:
                completion_rate = 100.0
    
    # 执行评分
    results = evaluate_session(session, first_completed, completion_rate)
    
    # 生成报告
    report = generate_report(session, results)
    
    # 输出报告
    reporter = ScoreReporter(report, session)
    reporter.print_report(args.format)
    
    # 保存报告
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            if args.format == 'json':
                f.write(reporter.to_json())
            elif args.format == 'markdown':
                f.write(reporter.to_markdown())
            else:
                f.write(reporter.to_table())
        print(f"\n报告已保存到: {output_path}")


def cmd_list(args):
    """列出会话命令"""
    sessions = list_sessions(args.project, args.limit)
    
    if not sessions:
        print("没有找到任何会话")
        return
    
    print(f"找到 {len(sessions)} 个会话:\n")
    print(f"{'序号':<4} {'会话ID':<38} {'修改时间':<20} {'摘要':<30}")
    print("-" * 100)
    
    for i, s in enumerate(sessions, 1):
        session_id = s['session_id'][:36]
        modified = s['modified'].strftime('%Y-%m-%d %H:%M:%S')
        summary = s['summary'][:30] if s['summary'] else "(无摘要)"
        print(f"{i:<4} {session_id:<38} {modified:<20} {summary:<30}")


def cmd_info(args):
    """显示会话详情"""
    # 查找会话文件
    session_file = None
    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if project_dir.is_dir():
            candidate = project_dir / f"{args.session}.jsonl"
            if candidate.exists():
                session_file = candidate
                break
    
    if not session_file:
        print(f"错误: 找不到会话 {args.session}")
        sys.exit(1)
    
    # 解析会话
    session = parse_session_file(session_file)
    
    print(f"会话ID: {session.session_id}")
    print(f"项目: {session.project_path}")
    print(f"消息总数: {len(session.messages)}")
    print(f"用户提示词: {len(session.user_prompts)} 条")
    print(f"AI回复: {len(session.assistant_responses)} 条")
    print(f"代码操作: {len(session.code_operations)} 个")
    print(f"代码行数: {session.total_lines} 行")
    
    if session.first_user_ts:
        print(f"首次请求: {session.first_user_ts}")
    if session.first_assistant_ts:
        print(f"首次回复: {session.first_assistant_ts}")
    
    print("\n=== 对话内容 ===\n")
    for msg in session.messages[:20]:  # 只显示前20条
        ts = msg.timestamp.strftime('%H:%M:%S')
        if msg.msg_type.value == 'user':
            content = msg.content[:80] if msg.content else "(tool_result)"
            print(f"[{ts}] 👤 USER: {content}")
        else:
            content = msg.content[:80] if msg.content else ""
            print(f"[{ts}] 🤖 AI: {content}")
            for tool in msg.tool_uses:
                print(f"         🔧 {tool.name}({tool.file_path or ''}) {tool.lines} lines")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Claude Code 评分工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  cc-eval --latest                    评估最新会话
  cc-eval --session <id>              评估指定会话
  cc-eval --latest --format json      输出JSON格式
  cc-eval list                        列出所有会话
  cc-eval info <session_id>           显示会话详情
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 评估命令（默认）
    eval_parser = subparsers.add_parser('eval', help='评估会话')
    eval_parser.add_argument('--session', '-s', help='会话ID')
    eval_parser.add_argument('--latest', '-l', action='store_true', help='评估最新会话')
    eval_parser.add_argument('--file', '-f', help='会话文件路径')
    eval_parser.add_argument('--project', '-p', help='项目路径')
    eval_parser.add_argument('--format', choices=['table', 'json', 'markdown'], default='table', help='输出格式')
    eval_parser.add_argument('--output', '-o', help='输出文件路径')
    eval_parser.add_argument('--first-completed', help='指定首次是否完成 (yes/no)')
    eval_parser.add_argument('--completion-rate', type=float, help='指定任务最终完成度 (0-100)')
    eval_parser.add_argument('--interactive', '-i', action='store_true', help='交互式确认首次完成度')
    eval_parser.add_argument('--no-agents', action='store_true', help='不包含agent文件')
    eval_parser.add_argument('--quiet', '-q', action='store_true', help='安静模式，只输出报告不输出进度信息')
    
    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出会话')
    list_parser.add_argument('--project', '-p', help='项目路径')
    list_parser.add_argument('--limit', '-n', type=int, default=10, help='显示数量')
    
    # 详情命令
    info_parser = subparsers.add_parser('info', help='显示会话详情')
    info_parser.add_argument('session', help='会话ID')
    
    args = parser.parse_args()
    
    # 如果没有子命令，默认使用eval
    if not args.command:
        # 检查是否有eval相关参数
        if hasattr(args, 'latest') or hasattr(args, 'session'):
            args.command = 'eval'
        else:
            parser.print_help()
            sys.exit(0)
    
    if args.command == 'eval':
        cmd_evaluate(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'info':
        cmd_info(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

