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
        out = run_python(code, tc['input'])
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

