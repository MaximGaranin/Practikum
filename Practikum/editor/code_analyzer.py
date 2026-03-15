import ast
import re
from typing import Dict, List, Tuple
import sys

# ── Совместимость Python 3.12+ ─────────────────────────────────
if sys.version_info >= (3, 12):
    # Создаём заглушки чтобы старый код не падал
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
        
        # Проверка синтаксиса
        if not self._check_syntax():
            return {
                'execution_mode': 'server',
                'reason': 'syntax_error',
                'can_use_pyodide': False,
                'issues': self.issues,
                'complexity_score': 0
            }
        
        # Анализ AST
        can_use_pyodide = self._analyze_ast()
        
        # Эвристический анализ
        self._analyze_heuristics()
        
        # Определение режима выполнения
        execution_mode = self._determine_execution_mode(can_use_pyodide)
        
        return {
            'execution_mode': execution_mode,
            'can_use_pyodide': can_use_pyodide,
            'issues': self.issues,
            'complexity_score': self.complexity_score,
            'reason': self._get_reason(execution_mode, can_use_pyodide)
        }
    
    def _check_syntax(self) -> bool:
        """Проверка синтаксиса кода"""
        try:
            ast.parse(self.code)
            return True
        except SyntaxError as e:
            self.issues.append(f"Синтаксическая ошибка: {str(e)}")
            return False
    
    def _analyze_ast(self) -> bool:
        """Анализ AST дерева кода"""
        try:
            tree = ast.parse(self.code)
            visitor = CodeVisitor()
            visitor.visit(tree)
            
            # Проверка импортов
            unsupported_imports = visitor.imports & self.PYODIDE_UNSUPPORTED
            if unsupported_imports:
                self.issues.append(
                    f"Неподдерживаемые библиотеки: {', '.join(unsupported_imports)}"
                )
                return False
            
            # Проверка файловых операций
            if visitor.has_file_operations:
                self.issues.append("Обнаружены операции с файлами")
                return False
            
            # Проверка системных вызовов
            if visitor.has_system_calls:
                self.issues.append("Обнаружены системные вызовы")
                return False
            
            # Подсчет сложности
            self.complexity_score = visitor.complexity_score
            
            return True
            
        except Exception as e:
            self.issues.append(f"Ошибка анализа: {str(e)}")
            return False
    
    def _analyze_heuristics(self):
        """Эвристический анализ кода"""
        
        # Количество строк
        lines = len([l for l in self.code.split('\n') if l.strip()])
        if lines > 150:
            self.complexity_score += 20
            self.issues.append(f"Большой размер кода: {lines} строк")
        
        # Проверка на бесконечные циклы
        if re.search(r'while\s+True\s*:', self.code):
            self.complexity_score += 50
            self.issues.append("Обнаружен потенциально бесконечный цикл")
        
        # Проверка на рекурсию
        if self._has_recursion():
            self.complexity_score += 10
            self.issues.append("Обнаружена рекурсия")
        
        # Проверка на вложенные циклы
        nested_loops = len(re.findall(r'for\s+\w+\s+in.*:\s*\n\s+.*for\s+\w+\s+in', self.code))
        if nested_loops > 0:
            self.complexity_score += nested_loops * 10
    
    def _has_recursion(self) -> bool:
        """Проверка на рекурсивные функции"""
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
        """Определение режима выполнения на основе анализа"""
        
        # Если не может быть выполнен в Pyodide
        if not can_use_pyodide:
            return 'server'
        
        # Если сложность высокая - на сервер
        if self.complexity_score > 50:
            return 'server'
        
        # Простой код - в браузер
        return 'client'
    
    def _get_reason(self, mode: str, can_use_pyodide: bool) -> str:
        """Получить причину выбора режима"""
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
    """Visitor для обхода AST дерева"""
    
    def __init__(self):
        self.imports: set = set()
        self.has_file_operations = False
        self.has_system_calls = False
        self.complexity_score = 0
        
    def visit_Import(self, node):
        """Обработка import statements"""
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Обработка from ... import statements"""
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Обработка вызовов функций"""
        # Проверка файловых операций
        if isinstance(node.func, ast.Name):
            if node.func.id in ['open', 'file']:
                self.has_file_operations = True
            # eval/exec/import как функция — тоже системный вызов
            if node.func.id in ['eval', 'exec', '__import__']:
                self.has_system_calls = True

        # Проверка системных вызовов через атрибут (os.system, subprocess.popen и т.д.)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['system', 'popen', 'exec', 'eval']:
                self.has_system_calls = True

        self.generic_visit(node)
    
    def visit_For(self, node):
        """Подсчет циклов"""
        self.complexity_score += 5
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Подсчет циклов while"""
        self.complexity_score += 5
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Подсчет функций"""
        self.complexity_score += 3
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Подсчет классов"""
        self.complexity_score += 10
        self.generic_visit(node)
