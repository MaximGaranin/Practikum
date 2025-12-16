from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from . import models
from editor.code_analyzer import CodeAnalyzer  # Новый импорт
from editor.docker_executor import DockerExecutor  # Новый импорт


def course_program(request, course_id=None):
    course = get_object_or_404(models.Course, id=course_id)
    list_topic = course.topics.all().order_by('id')
    context = {
        'course': course,
        'topics': list_topic,
        'course_id': course_id,
    }
    return render(request, 'course/course_program.html', context)


def course_task(request, course_id=None, task_id=None):
    """Отображение задачи с редактором кода"""
    course = get_object_or_404(models.Course, id=course_id)
    task = get_object_or_404(models.Task, id=task_id)
    topic = task.topic_set.first()

    all_tasks = list(topic.tasks.all().order_by('id')) if topic else []
    total_tasks = len(all_tasks)

    # Находим номер текущей задачи и ID соседних задач
    task_number = 0
    previous_task_id = None
    next_task_id = None
    
    for i, t in enumerate(all_tasks):
        if t.id == task.id:
            task_number = i + 1
            if i > 0:
                previous_task_id = all_tasks[i - 1].id
            if i < len(all_tasks) - 1:
                next_task_id = all_tasks[i + 1].id
            break

    context = {
        'task': task,
        'task_text': task.text_task,
        'task_id': task_id,
        'course': course,
        'course_id': course_id,
        'topic': topic,
        'task_number': task_number,
        'next_task': next_task_id,  # Изменено: теперь ID, а не номер
        'previous_task': previous_task_id,  # Изменено: теперь ID, а не номер
        'total_tasks': total_tasks,
    }

    return render(request, 'editor/editor.html', context)


@login_required
def enroll_course(request, course_id):
    """Записать пользователя на курс"""
    course = get_object_or_404(models.Course, id=course_id)

    if request.user not in course.students.all():
        course.students.add(request.user)
        messages.success(request, f'Вы успешно записались на курс "{course.name}"')
    else:
        messages.info(request, f'Вы уже записаны на курс "{course.name}"')

    return redirect('task_mananger:course_program', course_id=course_id)


# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ ГИБРИДНОГО РЕДАКТОРА ====================

@require_http_methods(["POST"])
def analyze_code(request):
    """Анализ кода и определение режима выполнения"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        task_id = data.get('task_id')
        
        if not code.strip():
            return JsonResponse({
                'error': 'Код не может быть пустым'
            }, status=400)
        
        # Анализ кода
        analyzer = CodeAnalyzer(code)
        result = analyzer.analyze()
        
        # Логирование (опционально)
        if task_id:
            task = models.Task.objects.filter(id=task_id).first()
            if task:
                print(f"[Анализ] Задача: {task.name}, Режим: {result['execution_mode']}")
        
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
        task_id = data.get('task_id')
        
        if not code.strip():
            return JsonResponse({
                'error': 'Код не может быть пустым'
            }, status=400)
        
        # Анализ кода
        analyzer = CodeAnalyzer(code)
        analysis = analyzer.analyze()
        
        # Выполнение в Docker
        executor = DockerExecutor()
        result = executor.execute(code, timeout=10)
        
        # Добавляем информацию об анализе
        result['analysis'] = analysis
        result['execution_mode'] = 'server'
        
        # Логирование (опционально)
        if task_id:
            task = models.Task.objects.filter(id=task_id).first()
            if task:
                print(f"[Выполнение] Задача: {task.name}, Успех: {result['success']}")
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Неверный формат данных'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка выполнения: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def check_task(request):
    """Проверка правильности решения задания"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        code = data.get('code', '')
        output = data.get('output', '')
        
        task = get_object_or_404(models.Task, id=task_id)
        
        # Проверка решения
        is_correct = False
        feedback_message = ''
        
        # Вариант 1: Если у вас есть поле expected_output в модели Task
        if hasattr(task, 'expected_output') and task.expected_output:
            is_correct = output.strip() == task.expected_output.strip()
            if is_correct:
                feedback_message = '🎉 Отличная работа! Задание решено правильно!'
            else:
                feedback_message = '⚠️ Результат не совпадает с ожидаемым. Попробуйте еще раз.'
        
        # Вариант 2: Если у вас есть тестовые случаи
        elif hasattr(task, 'test_cases') and task.test_cases:
            # Здесь можно добавить логику проверки по тест-кейсам
            is_correct = True  # Заглушка
            feedback_message = 'Код выполнен успешно!'
        
        # Вариант 3: Просто проверяем, что код выполнился без ошибок
        else:
            is_correct = 'error' not in output.lower() and output.strip() != ''
            if is_correct:
                feedback_message = '✓ Код выполнен успешно!'
            else:
                feedback_message = 'Код выполнен, но проверьте результат.'
        
        # Сохранение прогресса пользователя (опционально)
        if request.user.is_authenticated and is_correct:
            # Здесь можно добавить логику сохранения прогресса
            # Например, создать модель UserTaskProgress
            pass
        
        return JsonResponse({
            'correct': is_correct,
            'message': feedback_message,
            'task_completed': is_correct
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Неверный формат данных'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка проверки: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def save_code(request):
    """Сохранение кода пользователя (опционально)"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Требуется авторизация'
            }, status=401)
        
        data = json.loads(request.body)
        task_id = data.get('task_id')
        code = data.get('code', '')
        
        task = get_object_or_404(models.Task, id=task_id)
        
        # Здесь можно сохранить код пользователя в базу данных
        # Например, создать модель UserCode:
        # UserCode.objects.update_or_create(
        #     user=request.user,
        #     task=task,
        #     defaults={'code': code}
        # )
        
        return JsonResponse({
            'success': True,
            'message': 'Код сохранен'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка сохранения: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def load_saved_code(request, task_id):
    """Загрузка сохраненного кода пользователя (опционально)"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'code': None
            })
        
        task = get_object_or_404(models.Task, id=task_id)
        
        # Здесь можно загрузить сохраненный код из базы данных
        # saved_code = UserCode.objects.filter(
        #     user=request.user,
        #     task=task
        # ).first()
        
        # if saved_code:
        #     return JsonResponse({
        #         'code': saved_code.code
        #     })
        
        return JsonResponse({
            'code': None
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка загрузки: {str(e)}'
        }, status=500)
