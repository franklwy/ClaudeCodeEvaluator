"""
评分报告生成器
"""
import json
import unicodedata
from datetime import datetime
from typing import List, Optional

from ..models import EvaluationReport, EvaluationResult, SessionData


def get_char_width(char: str) -> int:
    """获取单个字符的显示宽度"""
    # 使用 Unicode East Asian Width 属性判断字符宽度
    # F(Fullwidth)=全角, W(Wide)=宽字符
    # 注意：A(Ambiguous)不包含，因为在大多数终端它们显示为1宽度
    w = unicodedata.east_asian_width(char)
    if w in ('F', 'W'):
        return 2
    return 1


def get_display_width(text: str) -> int:
    """计算字符串显示宽度（全角字符算2，半角算1）"""
    width = 0
    for char in text:
        width += get_char_width(char)
    return width


def truncate_text(text: str, max_width: int) -> str:
    """截断文本以适应显示宽度"""
    current_width = 0
    res = ""
    for char in text:
        char_width = get_char_width(char)
        if current_width + char_width > max_width:
            # 如果加上这个字符会超长，就不加了
            break
        res += char
        current_width += char_width
    return res


def pad_text(text: str, width: int, align: str = 'left') -> str:
    """填充文本以达到指定显示宽度"""
    # 先截断，防止超长破坏表格
    text = truncate_text(text, width)
    
    current_width = get_display_width(text)
    padding = max(0, width - current_width)
    
    if align == 'left':
        return text + ' ' * padding
    elif align == 'right':
        return ' ' * padding + text
    else:  # center
        left_pad = padding // 2
        right_pad = padding - left_pad
        return ' ' * left_pad + text + ' ' * right_pad


class ScoreReporter:
    """评分报告生成器"""
    
    def __init__(self, report: EvaluationReport, session: Optional[SessionData] = None):
        """
        初始化报告生成器
        
        Args:
            report: 评分报告
            session: 会话数据（可选，用于显示更多细节）
        """
        self.report = report
        self.session = session
    
    def to_table(self) -> str:
        """生成表格格式报告"""
        lines = []
        inner_width = 60
        
        # 标题
        lines.append("╔" + "═" * inner_width + "╗")
        title = "Claude Code 会话评分报告"
        lines.append("║" + pad_text(title, inner_width, 'center') + "║")
        lines.append("╠" + "═" * inner_width + "╣")
        
        # 会话信息
        # " 会话ID: " 宽度为 9
        label_width = 9
        val_width = inner_width - label_width
        
        val = self.report.session_id
        lines.append("║" + " 会话ID: " + pad_text(val, val_width) + "║")
        
        val = self.report.project_path
        lines.append("║" + " 项目:   " + pad_text(val, val_width) + "║")
        
        val = self.report.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        lines.append("║" + " 时间:   " + pad_text(val, val_width) + "║")
        
        # 评分明细
        lines.append("╠" + "═" * inner_width + "╣")
        
        # 定义列宽
        # 维度: 20, 得分: 10, 详情: 30. 总和 60.
        col1_w = 20
        col2_w = 10
        col3_w = 30
        
        header = "║" + pad_text(" 维度", col1_w) + pad_text(" 得分", col2_w) + pad_text(" 详情", col3_w) + "║"
        lines.append(header)
        lines.append("╠" + "─" * inner_width + "╣")
        
        for i, result in enumerate(self.report.results, 1):
            name = f" {i}. {result.name}"
            score = f" {result.score:.3f}"
            detail = f" {result.detail}" if result.detail else ""
            
            row = "║" + pad_text(name, col1_w) + pad_text(score, col2_w) + pad_text(detail, col3_w) + "║"
            lines.append(row)
        
        # 总分
        lines.append("╠" + "═" * inner_width + "╣")
        footer = "║" + pad_text(" 综合得分", col1_w) + pad_text(f" {self.report.total_score:.3f}", col2_w) + pad_text(" (加权平均)", col3_w) + "║"
        lines.append(footer)
        lines.append("╚" + "═" * inner_width + "╝")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """生成JSON格式报告"""
        data = {
            'session_id': self.report.session_id,
            'project_path': self.report.project_path,
            'timestamp': self.report.timestamp.isoformat(),
            'total_score': self.report.total_score,
            'results': [
                {
                    'name': r.name,
                    'score': r.score,
                    'weight': r.weight,
                    'weighted_score': r.weighted_score,
                    'raw_value': r.raw_value,
                    'detail': r.detail
                }
                for r in self.report.results
            ]
        }
        
        if self.session:
            data['session_info'] = {
                'prompt_count': len(self.session.user_prompts),
                'assistant_count': len(self.session.assistant_responses),
                'code_operations': len(self.session.code_operations),
                'total_lines': self.session.total_lines
            }
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def to_markdown(self) -> str:
        """生成Markdown格式报告"""
        lines = []
        
        lines.append("# Claude Code 会话评分报告")
        lines.append("")
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"- **会话ID**: `{self.report.session_id}`")
        lines.append(f"- **项目**: `{self.report.project_path}`")
        lines.append(f"- **时间**: {self.report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        lines.append("## 评分明细")
        lines.append("")
        lines.append("| 序号 | 维度 | 得分 | 详情 |")
        lines.append("|------|------|------|------|")
        
        for i, result in enumerate(self.report.results, 1):
            detail = result.detail.replace("|", "\\|") if result.detail else ""
            lines.append(f"| {i} | {result.name} | {result.score:.3f} | {detail} |")
        
        lines.append("")
        lines.append(f"## 综合得分: **{self.report.total_score:.3f}**")
        lines.append("")
        
        if self.session and self.session.code_operations:
            lines.append("## 生成的代码")
            lines.append("")
            for op in self.session.code_operations:
                lines.append(f"### {op.file_path}")
                lines.append(f"- 行数: {op.lines}")
                lines.append("")
                lines.append("```python")
                lines.append(op.content[:500] if len(op.content) > 500 else op.content)
                if len(op.content) > 500:
                    lines.append("# ... (truncated)")
                lines.append("```")
                lines.append("")
        
        return "\n".join(lines)
    
    def print_report(self, format: str = 'table'):
        """
        打印报告
        
        Args:
            format: 输出格式 (table/json/markdown)
        """
        if format == 'json':
            print(self.to_json())
        elif format == 'markdown':
            print(self.to_markdown())
        else:
            print(self.to_table())


def generate_report(
    session: SessionData,
    results: List[EvaluationResult]
) -> EvaluationReport:
    """
    生成评分报告
    
    Args:
        session: 会话数据
        results: 评分结果列表
    
    Returns:
        EvaluationReport: 完整评分报告
    """
    report = EvaluationReport(
        session_id=session.session_id,
        project_path=session.project_path,
        timestamp=datetime.now(),
        results=results
    )
    report.compute_total_score()
    return report
