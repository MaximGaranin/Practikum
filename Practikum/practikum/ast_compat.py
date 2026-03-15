"""Патч совместимости ast для Python 3.12+.
ast.Str, ast.Num, ast.Bytes удалены в Python 3.12 — этот модуль их восстанавливает.
Импортируй ПЕРВЫМ в tests.py и conftest.py.
"""
import ast

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

if not hasattr(ast, 'NameConstant'):
    class _AstNameConstant:
        @classmethod
        def __instancecheck__(cls, node):
            return isinstance(node, ast.Constant) and isinstance(node.value, (bool, type(None)))
    ast.NameConstant = _AstNameConstant()
