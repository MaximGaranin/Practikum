from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from .docker_executor import DockerExecutor
from .code_analyzer import CodeAnalyzer
from practikum.checker import run_python  # локальный запуск через subprocess


def editor_view(request, task_id=None):
    """Главная страница редактора."""
    task = None
    if task_id:
        from Logistic_Task.models import Task
        task = get_object_or_404(Task, id=task_id)
    return render(request, 'editor/editor.html', {'task': task})


@require_http_methods(["POST"])
def analyze_code(request):
    """Анализ кода — определяет режим выполнения."""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        if not code.strip():
            return JsonResponse({'error': 'Код не может быть пустым'}, status=400)
        analyzer = CodeAnalyzer(code)
        result = analyzer.analyze()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def execute_code(request):
    """
    Умный запуск: сначала анализируем код.
    Если execution_mode == 'client' → запускаем локально (subprocess).
    Если execution_mode == 'server' → запускаем в Docker (офлайн, без сети).
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        stdin = data.get('stdin', '')

        if not code.strip():
            return JsonResponse({'error': 'Код не может быть пустым'}, status=400)

        # Шаг 1: анализируем сложность
        analyzer = CodeAnalyzer(code)
        analysis = analyzer.analyze()
        mode = analysis.get('execution_mode', 'server')  # 'client' или 'server'

        # Шаг 2: запускаем нужным способом
        if mode == 'client':
            # Простой код — локальный subprocess, быстро
            raw = run_python(code, stdin, time_limit=5)
            return JsonResponse({
                'success': raw['returncode'] == 0,
                'output': raw['stdout'],
                'error': raw['stderr'],
                'execution_mode': 'local',   # ← показываем в UI
                'complexity_score': analysis['complexity_score'],
            })
        else:
            # Сложный код — Docker без сети (офлайн)
            executor = DockerExecutor()
            result = executor.execute(code)
            result['execution_mode'] = 'docker'  # ← показываем в UI
            result['complexity_score'] = analysis['complexity_score']
            result['reason'] = analysis.get('reason', '')
            return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

