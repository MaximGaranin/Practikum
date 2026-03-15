import ast
import re
from typing import Dict, List, Tuple
import sys

# Патч Python 3.12+ — до любых других импортов
if not hasattr(ast, 'Str'):
    class _AstStr:
        @classmethod
        def __instancecheck__(cls, node):
            return isinstance(node, ast.Constant) and isinstance(node.value, str)
    ast.Str = _AstStr()

if not hasattr(ast, 'Num'):
    class _AstNum:
        @classmethod
        def __instancecheck__(cls, node):
            return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
    ast.Num = _AstNum()

if not hasattr(ast, 'Bytes'):
    class _AstBytes:
        @classmethod
        def __instancecheck__(cls, node):
            return isinstance(node, ast.Constant) and isinstance(node.value, bytes)
    ast.Bytes = _AstBytes()


class CodeAnalyzer:
    """Анализирует Python код и определяет оптимальный способ выполнения"""
    
    # Библиотеки, недоступные в Pyodide
    PYODIDE_UNSUPPORTED = {
        'subprocess', 'multiprocessing', 'threading', 'os',
        'socket', 'ssl', 'sqlite3', 'psycopg2',
        'mysql', 'django', 'flask', 'fastapi'
    }
    
    # Библиотеки, поддерживаемые в Pyodide
    PYODIDE_SUPPORTED = {
        'numpy', 'pandas', 'matplotlib', 'scipy', 'scikit-learn',
        'regex', 'micropip', 'pyodide', 'js', 'pprint'
    }
    
    def __init__(self, code: str):
        self.code = code
        self.issues: List[str] = []
        self.complexity_score = 0
        
    def analyze(self) -> Dict[str, any]:
        """Главный метод анализа"""
        
        if not self._check_syntax():
            return {
                'execution_mode': 'server',
                'reason': 'syntax_error',
                'can_use_pyodide': False,
                'issues': self.issues,
                'complexity_score': 0
            }
        
        can_use_pyodide = self._analyze_ast()
        self._analyze_heuristics()
        execution_mode = self._determine_execution_mode(can_use_pyodide)
        
        return {
            'execution_mode': execution_mode,
            'can_use_pyodide': can_use_pyodide,
            'issues': self.issues,
            'complexity_score': self.complexity_score,
            'reason': self._get_reason(execution_mode, can_use_pyodide)
        }
    
    def _check_syntax(self) -> bool:
        try:
            ast.parse(self.code)
            return True
        except SyntaxError as e:
            self.issues.append(f"Синтаксическая ошибка: {str(e)}")
            return False
    
    def _analyze_ast(self) -> bool:
        try:
            tree = ast.parse(self.code)
            visitor = CodeVisitor()
            visitor.visit(tree)
            
            unsupported_imports = visitor.imports & self.PYODIDE_UNSUPPORTED
            if unsupported_imports:
                self.issues.append(
                    f"Неподдерживаемые библиотеки: {', '.join(unsupported_imports)}"
                )
                return False
            
            if visitor.has_file_operations:
                self.issues.append("Обнаружены операции с файлами")
                return False
            
            if visitor.has_system_calls:
                self.issues.append("Обнаружены системные вызовы")
                return False
            
            self.complexity_score = visitor.complexity_score
            return True
            
        except Exception as e:
            self.issues.append(f"Ошибка анализа: {str(e)}")
            return False
    
    def _analyze_heuristics(self):
        lines = len([l for l in self.code.split('\n') if l.strip()])
        if lines > 150:
            self.complexity_score += 20
            self.issues.append(f"Большой размер кода: {lines} строк")
        
        if re.search(r'while\s+True\s*:', self.code):
            self.complexity_score += 50
            self.issues.append("Обнаружен потенциально бесконечный цикл")
        
        if self._has_recursion():
            self.complexity_score += 10
            self.issues.append("Обнаружена рекурсия")
        
        nested_loops = len(re.findall(r'for\s+\w+\s+in.*:\s*\n\s+.*for\s+\w+\s+in', self.code))
        if nested_loops > 0:
            self.complexity_score += nested_loops * 10
    
    def _has_recursion(self) -> bool:
        try:
            tree = ast.parse(self.code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name) and child.func.id == func_name:
                                return True
            return False
        except:
            return False
    
    def _determine_execution_mode(self, can_use_pyodide: bool) -> str:
        if not can_use_pyodide:
            return 'server'
        if self.complexity_score > 50:
            return 'server'
        return 'client'
    
    def _get_reason(self, mode: str, can_use_pyodide: bool) -> str:
        if mode == 'server':
            if not can_use_pyodide:
                return "Код содержит неподдерживаемые функции"
            elif self.complexity_score > 50:
                return f"Высокая сложность кода (score: {self.complexity_score})"
            else:
                return "Требуется серверное выполнение"
        else:
            return "Код может быть выполнен в браузере"


class CodeVisitor(ast.NodeVisitor):
    """Виситор для обхода AST дерева"""
    
    def __init__(self):
        self.imports: set = set()
        self.has_file_operations = False
        self.has_system_calls = False
        self.complexity_score = 0
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in ['open', 'file']:
                self.has_file_operations = True
            if node.func.id in ['eval', 'exec', '__import__']:
                self.has_system_calls = True
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['system', 'popen', 'exec', 'eval']:
                self.has_system_calls = True
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.complexity_score += 5
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.complexity_score += 5
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        self.complexity_score += 3
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.complexity_score += 10
        self.generic_visit(node)
