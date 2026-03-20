import os
import subprocess
import tempfile
import time
from typing import Dict


class DockerExecutor:
    """Выполнение кода в Docker контейнере (офлайн-режим).

    Исправления по сравнению с предыдущей версией:
    - Код пишется в файл, а не передаётся через python -c
    - stdin передаётся через subprocess (input=)
    - Корректная обработка ошибок
    - Удалён импорт docker SDK (не нужен)
    """

    IMAGE = 'python:3.11-slim'

    def execute(self, code: str, stdin: str = '', timeout: int = 10) -> Dict:
        """Выполнить код в изолированном контейнере."""
        with tempfile.NamedTemporaryFile(
            suffix='.py', mode='w', encoding='utf-8', delete=False
        ) as f:
            f.write(code)
            fname = f.name

        start_time = time.time()
        try:
            result = subprocess.run(
                [
                    'docker', 'run', '--rm',
                    '--network', 'none',
                    '--memory', '128m',
                    '--cpus', '0.5',
                    '--pids-limit', '50',
                    '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges',
                    '-i',
                    '-v', f'{fname}:/tmp/solution.py:ro',
                    self.IMAGE,
                    'python3', '/tmp/solution.py',
                ],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            execution_time = round(time.time() - start_time, 3)

            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout.strip(),
                    'error': result.stderr.strip(),
                    'execution_time': execution_time,
                }
            else:
                return {
                    'success': False,
                    'output': result.stdout.strip(),
                    'error': result.stderr.strip() or 'Ошибка выполнения',
                    'execution_time': execution_time,
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': 'Превышено время выполнения',
                'execution_time': timeout,
            }
        except FileNotFoundError:
            return {
                'success': False,
                'output': '',
                'error': 'Docker не найден. Убедитесь, что Docker установлен и запущен.',
                'execution_time': 0,
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': f'Ошибка выполнения: {str(e)}',
                'execution_time': 0,
            }
        finally:
            if os.path.exists(fname):
                os.unlink(fname)
