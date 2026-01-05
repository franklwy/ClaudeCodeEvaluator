"""
维度6: 代码质量评分器
"""
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Tuple, Optional

from ..models import SessionData
from ..config import LANGUAGE_CONFIG
from .base import BaseEvaluator


class CodeQualityEvaluator(BaseEvaluator):
    """
    代码质量评分
    
    逻辑：
    - 分析生成代码的圈复杂度（使用radon）
    - 分析可维护性指数（使用radon mi）
    - 检查Lint错误（使用flake8）
    - 综合三项指标加权计算最终分数
    
    公式：
    - complexity_score = max(0, 1 - (avg_complexity - 1) / (max_complexity - 1))
    - maintainability_score = mi_score / 100
    - lint_score = max(0, 1 - lint_errors / max_lint_errors)
    - final_score = complexity_score * w1 + maintainability_score * w2 + lint_score * w3
    """
    
    @property
    def name(self) -> str:
        return "代码质量"
    
    def evaluate(self, session: SessionData) -> float:
        if not session.code_operations:
            self._raw_value = {'complexity': 0, 'maintainability': 100, 'lint_errors': 0}
            self._detail = "无代码生成"
            return 1.0
        
        # 配置参数
        complexity_weight = self.config.get('complexity_weight', 0.4)
        maintainability_weight = self.config.get('maintainability_weight', 0.4)
        lint_weight = self.config.get('lint_weight', 0.2)
        max_complexity = self.config.get('max_complexity', 20)
        max_lint_errors = self.config.get('max_lint_errors', 10)
        
        # 收集所有Python代码
        python_codes = []
        for op in session.code_operations:
            ext = Path(op.file_path).suffix.lower()
            if ext == '.py' and op.content:
                python_codes.append((op.file_path, op.content))
        
        if not python_codes:
            # 非Python代码，使用简化评估
            self._raw_value = {'complexity': 1, 'maintainability': 80, 'lint_errors': 0}
            self._detail = "非Python代码（简化评估）"
            return 0.85
        
        # 分析代码质量
        avg_complexity, avg_mi, total_lint = self._analyze_python_codes(python_codes)
        
        self._raw_value = {
            'complexity': avg_complexity,
            'maintainability': avg_mi,
            'lint_errors': total_lint
        }
        
        # 计算各项得分
        # 圈复杂度: 1是最好，越高越差
        if avg_complexity <= 1:
            complexity_score = 1.0
        elif avg_complexity >= max_complexity:
            complexity_score = 0.0
        else:
            complexity_score = 1 - (avg_complexity - 1) / (max_complexity - 1)
        
        # 可维护性: 0-100，越高越好
        maintainability_score = avg_mi / 100.0
        
        # Lint错误: 0是最好，越多越差
        if total_lint <= 0:
            lint_score = 1.0
        elif total_lint >= max_lint_errors:
            lint_score = 0.0
        else:
            lint_score = 1 - total_lint / max_lint_errors
        
        # 加权计算
        final_score = (
            complexity_score * complexity_weight +
            maintainability_score * maintainability_weight +
            lint_score * lint_weight
        )
        
        self._detail = f"复杂度:{avg_complexity:.1f} 可维护性:{avg_mi:.0f} Lint:{total_lint}"
        
        return max(0.0, min(1.0, final_score))
    
    def _analyze_python_codes(self, codes: list) -> Tuple[float, float, int]:
        """
        分析Python代码质量
        
        Args:
            codes: [(file_path, content), ...]
        
        Returns:
            (avg_complexity, avg_maintainability, total_lint_errors)
        """
        complexities = []
        maintainabilities = []
        lint_errors = 0
        
        for file_path, content in codes:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                # 分析圈复杂度
                cc = self._get_cyclomatic_complexity(temp_path)
                if cc is not None:
                    complexities.append(cc)
                
                # 分析可维护性
                mi = self._get_maintainability_index(temp_path)
                if mi is not None:
                    maintainabilities.append(mi)
                
                # 检查Lint错误
                lint = self._get_lint_errors(temp_path)
                lint_errors += lint
            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        avg_complexity = sum(complexities) / len(complexities) if complexities else 1.0
        avg_mi = sum(maintainabilities) / len(maintainabilities) if maintainabilities else 80.0
        
        return avg_complexity, avg_mi, lint_errors
    
    def _get_cyclomatic_complexity(self, file_path: str) -> Optional[float]:
        """获取圈复杂度（使用radon）"""
        try:
            result = subprocess.run(
                ['radon', 'cc', file_path, '-a', '-s'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # 解析输出，找到平均复杂度
            # 输出格式: "Average complexity: A (1.0)"
            for line in result.stdout.split('\n'):
                if 'Average complexity' in line:
                    # 提取数字
                    parts = line.split('(')
                    if len(parts) > 1:
                        num_str = parts[1].rstrip(')')
                        return float(num_str)
            return 1.0  # 默认复杂度
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            return None
    
    def _get_maintainability_index(self, file_path: str) -> Optional[float]:
        """获取可维护性指数（使用radon mi）"""
        try:
            result = subprocess.run(
                ['radon', 'mi', file_path, '-s'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # 解析输出
            # 输出格式: "path.py - A (100.00)"
            for line in result.stdout.split('\n'):
                if file_path in line or '.py' in line:
                    parts = line.split('(')
                    if len(parts) > 1:
                        num_str = parts[1].rstrip(')')
                        return float(num_str)
            return 80.0  # 默认可维护性
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            return None
    
    def _get_lint_errors(self, file_path: str) -> int:
        """获取Lint错误数（使用flake8）"""
        try:
            result = subprocess.run(
                ['flake8', file_path, '--count', '--select=E,W,F'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # 统计错误行数
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                # 最后一行是总数
                try:
                    return int(lines[-1])
                except ValueError:
                    return len(lines)
            return 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0

