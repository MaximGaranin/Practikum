from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .docker_executor import DockerExecutor
from .code_analyzer import CodeAnalyzer


def editor_view(request, task_id=None):
    task = None
    if task_id:
        from Logistic_Task.models import Task
        task = get_object_or_404(Task, id=task_id)
    return render(request, 'editor/editor.html', {'task': task})


@csrf_exempt  # ← добавить
@require_http_methods(["POST"])
def analyze_code(request):
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


@csrf_exempt  # ← добавить
@require_http_methods(["POST"])
def execute_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        if not code.strip():
            return JsonResponse({'error': 'Код не может быть пустым'}, status=400)

        analyzer = CodeAnalyzer(code)
        analysis = analyzer.analyze()
        mode = analysis.get('execution_mode', 'server')

        if mode == 'client':
            from practikum.checker import run_python
            raw = run_python(code, '', time_limit=5)
            return JsonResponse({
                'success': raw['returncode'] == 0,
                'output': raw['stdout'],
                'error': raw['stderr'],
                'execution_mode': 'local',
                'complexity_score': analysis['complexity_score'],
            })
        else:
            executor = DockerExecutor()
            result = executor.execute(code)
            result['execution_mode'] = 'docker'
            result['complexity_score'] = analysis['complexity_score']
            result['reason'] = analysis.get('reason', '')
            return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

