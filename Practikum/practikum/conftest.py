import ast

# Патч Python 3.12+ — ДО всех остальных импортов
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

# ── Дальше без изменений ──────────────────────────────────────
import django
import pytest
from django.conf import settings


def pytest_configure():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }

# ... остальные фикстуры без изменений

