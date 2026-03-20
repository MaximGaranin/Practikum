import os
import subprocess
import tempfile


BANNED_PATTERNS = [
    'import os',
    'import sys',
    'import subprocess',
    'import shutil',
    'import socket',
    'import requests',
    'import urllib',
    'from os',
    'from sys',
    'from subprocess',
    'from shutil',
    'from socket',
    '__import__',
    'open(',
    'exec(',
    'eval(',
]


def is_code_safe(code: str) -> bool:
    lowered = code.lower()
    return not any(pattern in lowered for pattern in BANNED_PATTERNS)


def run_python(code: str, stdin: str, time_limit: int = 3) -> dict:
    with tempfile.NamedTemporaryFile(
        suffix='.py',
        mode='w',
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(code)
        fname = f.name

    try:
        result = subprocess.run(
            ['python3', fname],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=time_limit
        )
        return {
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            'stdout': '',
            'stderr': 'Превышено время выполнения',
            'returncode': -1,
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
        }
    finally:
        if os.path.exists(fname):
            os.unlink(fname)


def check_submission(code: str, test_cases: list) -> dict:
    if not is_code_safe(code):
        return {
            'status': 'error',
            'passed': 0,
            'total': len(test_cases),
            'results': [],
            'error': 'Код содержит запрещённые конструкции.',
        }

    if not test_cases:
        return {
            'status': 'error',
            'passed': 0,
            'total': 0,
            'results': [],
            'error': 'Для задания не найдены тест-кейсы.',
        }

    results = []
    passed = 0
    has_runtime_error = False

    for i, tc in enumerate(test_cases, start=1):
        runner = run_python_docker if is_complex_code(code) else run_python
        out = runner(code, tc['input'])
        expected = tc['expected'].strip()

        if out['returncode'] != 0:
            has_runtime_error = True
            results.append({
                'test': i,
                'passed': False,
                'expected': expected,
                'got': out['stdout'],
                'error': out['stderr'] or 'Ошибка выполнения',
            })
            continue

        got = out['stdout']
        ok = got == expected

        if ok:
            passed += 1

        results.append({
            'test': i,
            'passed': ok,
            'expected': expected,
            'got': got,
            'error': out['stderr'],
        })

    if passed == len(test_cases):
        status = 'accepted'
    elif has_runtime_error:
        status = 'error'
    else:
        status = 'wrong_answer'

    return {
        'status': status,
        'passed': passed,
        'total': len(test_cases),
        'results': results,
    }


COMPLEXITY_THRESHOLD = 50


def is_complex_code(code: str) -> bool:
    """Сложный = много строк ИЛИ тяжёлые библиотеки."""
    lines = [l for l in code.strip().splitlines() if l.strip()]
    heavy = ['numpy', 'pandas', 'scipy', 'matplotlib', 'sklearn']
    return len(lines) > COMPLEXITY_THRESHOLD or any(h in code for h in heavy)


def run_python_docker(code: str, stdin: str, time_limit: int = 10) -> dict:
    """Запуск кода в Docker-контейнере без сети (офлайн-режим).

    Исправления:
    - Код пишется во временный файл и монтируется в контейнер (вместо -c)
    - stdin передаётся через subprocess (поддержка input())
    - Корректная обработка ошибок контейнера и отсутствия Docker
    """
    with tempfile.NamedTemporaryFile(
        suffix='.py',
        mode='w',
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(code)
        fname = f.name

    try:
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '--network', 'none',
                '--memory', '128m',
                '--cpus', '0.5',
                '-i',
                '-v', f'{fname}:/tmp/solution.py:ro',
                'python:3.11-slim',
                'python3', '/tmp/solution.py',
            ],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=time_limit,
        )
        return {
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            'stdout': '',
            'stderr': 'Превышено время выполнения',
            'returncode': -1,
        }
    except FileNotFoundError:
        return {
            'stdout': '',
            'stderr': 'Docker не найден. Убедитесь, что Docker установлен и запущен.',
            'returncode': -1,
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
        }
    finally:
        if os.path.exists(fname):
            os.unlink(fname)
