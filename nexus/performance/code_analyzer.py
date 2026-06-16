"""
NexusCore — محلل الكود
يحلل جودة الكود ويقترح تحسينات (قراءة فقط — لا تعديل).
"""
import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.performance.code_analyzer")


@dataclass
class CodeIssue:
    file: str
    line: int
    issue_type: str    # complexity / style / security / performance
    severity: str      # info / warning / error
    message: str
    suggestion: str


@dataclass
class FileAnalysis:
    file_path: str
    lines: int
    functions: int
    classes: int
    complexity_score: float
    issues: List[CodeIssue] = field(default_factory=list)


class CodeAnalyzer:
    """يحلل ملفات Python ويولد تقارير الجودة"""

    MAX_FUNCTION_LINES = 50
    MAX_COMPLEXITY = 10

    def __init__(self):
        self.analyses: List[FileAnalysis] = []
        logger.info("🔬 CodeAnalyzer initialized (read-only)")

    def analyze_file(self, file_path: str) -> Optional[FileAnalysis]:
        p = Path(file_path)
        if not p.exists() or p.suffix != ".py":
            return None
        try:
            source = p.read_text(encoding="utf-8")
            tree   = ast.parse(source)
        except Exception as exc:
            logger.warning(f"Parse error {file_path}: {exc}")
            return None

        lines     = source.count("\n") + 1
        functions = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        classes   = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
        issues    = self._check_issues(tree, file_path, source)
        complexity = self._estimate_complexity(tree)

        analysis = FileAnalysis(
            file_path=str(p), lines=lines, functions=functions,
            classes=classes, complexity_score=complexity, issues=issues,
        )
        self.analyses.append(analysis)
        return analysis

    def analyze_directory(self, directory: str,
                          exclude: Optional[List[str]] = None) -> List[FileAnalysis]:
        exclude = exclude or ["__pycache__", ".git", "venv", "node_modules"]
        results = []
        for p in Path(directory).rglob("*.py"):
            if any(ex in str(p) for ex in exclude):
                continue
            a = self.analyze_file(str(p))
            if a:
                results.append(a)
        return results

    def _check_issues(self, tree: ast.AST,
                      file_path: str, source: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                body_lines = (node.end_lineno or 0) - node.lineno
                if body_lines > self.MAX_FUNCTION_LINES:
                    issues.append(CodeIssue(
                        file=file_path, line=node.lineno,
                        issue_type="complexity", severity="warning",
                        message=f"الدالة '{node.name}' طويلة ({body_lines} سطر)",
                        suggestion="فكّك الدالة إلى دوال أصغر",
                    ))
            if isinstance(node, ast.Exec if hasattr(ast, "Exec") else type(None)):
                issues.append(CodeIssue(
                    file=file_path, line=getattr(node, "lineno", 0),
                    issue_type="security", severity="error",
                    message="استخدام exec() خطير",
                    suggestion="تجنب exec() — استخدم بدائل آمنة",
                ))
        return issues

    def _estimate_complexity(self, tree: ast.AST) -> float:
        branches = sum(
            1 for n in ast.walk(tree)
            if isinstance(n, (ast.If, ast.For, ast.While, ast.Try,
                              ast.ExceptHandler, ast.With))
        )
        return min(10.0, branches / 5)

    def get_summary(self) -> Dict:
        if not self.analyses:
            return {}
        total_issues = sum(len(a.issues) for a in self.analyses)
        return {
            "files_analyzed": len(self.analyses),
            "total_lines": sum(a.lines for a in self.analyses),
            "total_issues": total_issues,
            "avg_complexity": round(
                sum(a.complexity_score for a in self.analyses) / len(self.analyses), 2
            ),
        }
