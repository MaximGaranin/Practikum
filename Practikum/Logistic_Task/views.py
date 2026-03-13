from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from . import models
from editor.code_analyzer import CodeAnalyzer
from editor.docker_executor import DockerExecutor
from Logistic_Task.models import UserTaskProgress
import math

def course_program(request, course_id=None):
    course = get_object_or_404(models.Course, id=course_id)
    list_topic = course.topics.all().order_by('id')

    # Считаем прогресс по курсу
    progress_percent = 0
    progress_ring_offset = 94.2

    if request.user.is_authenticated:
        total_tasks = models.Task.objects.filter(
            topic__course=course
        ).distinct().count()

        if total_tasks > 0:
            completed = UserTaskProgress.objects.filter(
                user=request.user,
                task__topic__course=course,
                is_completed=True
            ).count()
            progress_percent = round((completed / total_tasks) * 100)
            progress_ring_offset = round(94.2 - (94.2 * progress_percent / 100), 2)
    context = {
        'course': course,
        'topics': list_topic,
        'course_id': course_id,
        'progress_percent': progress_percent,
        'progress_ring_offset': progress_ring_offset,
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
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        code = data.get('code', '')
        output = data.get('output', '')

        task = get_object_or_404(models.Task, id=task_id)

        is_correct = False
        feedback_message = ''

        if task.expected_output:
            is_correct = output.strip() == task.expected_output.strip()
            feedback_message = '🎉 Задание решено правильно!' if is_correct else '⚠️ Результат не совпадает. Попробуйте ещё раз.'
        else:
            is_correct = bool(output.strip()) and 'error' not in output.lower()
            feedback_message = '✓ Код выполнен успешно!' if is_correct else 'Проверьте результат.'

        # Сохраняем прогресс
        if request.user.is_authenticated:
            from django.utils.timezone import now
            progress, created = models.UserTaskProgress.objects.get_or_create(
                user=request.user,
                task=task
            )
            progress.code = code
            progress.attempts += 1
            if is_correct and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = now()
            progress.save()

        return JsonResponse({
            'correct': is_correct,
            'message': feedback_message,
            'task_completed': is_correct
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Ошибка проверки: {str(e)}'}, status=500)


@require_http_methods(["POST"])
def save_code(request):
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Требуется авторизация'}, status=401)

        data = json.loads(request.body)
        task_id = data.get('task_id')
        code = data.get('code', '')

        task = get_object_or_404(models.Task, id=task_id)

        progress, _ = models.UserTaskProgress.objects.get_or_create(
            user=request.user,
            task=task
        )
        progress.code = code
        progress.save()

        return JsonResponse({'success': True, 'message': 'Код сохранён'})

    except Exception as e:
        return JsonResponse({'error': f'Ошибка сохранения: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def load_saved_code(request, task_id):
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'code': None})

        task = get_object_or_404(models.Task, id=task_id)
        progress = models.UserTaskProgress.objects.filter(
            user=request.user,
            task=task
        ).first()

        return JsonResponse({'code': progress.code if progress else None})

    except Exception as e:
        return JsonResponse({'error': f'Ошибка загрузки: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def search_courses(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    courses = models.Course.objects.filter(name__icontains=query)
    results = [{'id': c.id, 'name': c.name} for c in courses]
    return JsonResponse({'results': results})
