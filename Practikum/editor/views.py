from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .code_analyzer import CodeAnalyzer
from .docker_executor import DockerExecutor

def editor_view(request):
    """Главная страница редактора"""
    return render(request, 'editor/editor.html')

@require_http_methods(["POST"])
def analyze_code(request):
    """Анализ кода и определение режима выполнения"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        
        if not code.strip():
            return JsonResponse({
                'error': 'Код не может быть пустым'
            }, status=400)
        
        # Анализ кода
        analyzer = CodeAnalyzer(code)
        result = analyzer.analyze()
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Неверный формат данных'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка анализа: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def execute_code(request):
    """Выполнение кода на сервере (Docker)"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        
        if not code.strip():
            return JsonResponse({
                'error': 'Код не может быть пустым'
            }, status=400)
        
        # Сначала анализируем код
        analyzer = CodeAnalyzer(code)
        analysis = analyzer.analyze()
        
        # Выполняем в Docker
        executor = DockerExecutor()
        result = executor.execute(code)
        
        # Добавляем информацию об анализе
        result['analysis'] = analysis
        result['execution_mode'] = 'server'
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Неверный формат данных'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка выполнения: {str(e)}'
        }, status=500)

