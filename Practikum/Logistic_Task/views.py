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
from practikum.checker import run_python
import math

def course_program(request, course_id=None):
    course = get_object_or_404(models.Course, id=course_id)
    list_topic = course.topics.all().order_by('id')

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
        'next_task': next_task_id,
        'previous_task': previous_task_id,
        'total_tasks': total_tasks,
    }

    return render(request, 'editor/editor.html', context)


@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(models.Course, id=course_id)

    if request.user not in course.students.all():
        course.students.add(request.user)
        messages.success(request, f'Вы успешно записались на курс "{course.name}"')
    else:
        messages.info(request, f'Вы уже записаны на курс "{course.name}"')

    return redirect('task_mananger:course_program', course_id=course_id)


@require_http_methods(["POST"])
def analyze_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        task_id = data.get('task_id')

        if not code.strip():
            return JsonResponse({'error': 'Код не может быть пустым'}, status=400)

        analyzer = CodeAnalyzer(code)
        result = analyzer.analyze()

        if task_id:
            task = models.Task.objects.filter(id=task_id).first()
            if task:
                print(f"[Анализ] Задача: {task.name}, Режим: {result['execution_mode']}")

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Ошибка анализа: {str(e)}'}, status=500)


@require_http_methods(["POST"])
def execute_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        task_id = data.get('task_id')

        if not code.strip():
            return JsonResponse({'error': 'Код не может быть пустым'}, status=400)

        analyzer = CodeAnalyzer(code)
        analysis = analyzer.analyze()

        executor = DockerExecutor()
        result = executor.execute(code, timeout=10)

        result['analysis'] = analysis
        result['execution_mode'] = 'server'

        if task_id:
            task = models.Task.objects.filter(id=task_id).first()
            if task:
                print(f"[Выполнение] Задача: {task.name}, Успех: {result['success']}")

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Ошибка выполнения: {str(e)}'}, status=500)


@require_http_methods(["POST"])
def check_task(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        code = data.get('code', '')

        task = get_object_or_404(models.Task, id=task_id)

        # Получаем все тест-кейсы задания
        test_cases = list(task.testcase_set.values('input', 'expected', 'is_hidden'))

        is_correct = False
        feedback_message = ''

        if test_cases:
            # Прогоняем код через каждый тест-кейс
            failed_cases = []
            for tc in test_cases:
                result = run_python(code, tc['input'])
                actual = result.get('stdout', '').strip()
                expected = tc['expected'].strip()
                if actual != expected:
                    failed_cases.append({
                        'is_hidden': tc['is_hidden'],
                        'input': tc['input'],
                        'expected': expected,
                        'actual': actual,
                    })

            if not failed_cases:
                is_correct = True
                feedback_message = '🎉 Задание решено правильно!'
            else:
                # Показываем только открытые провалывшие кейсы
                visible_fails = [f for f in failed_cases if not f['is_hidden']]
                hidden_fails  = [f for f in failed_cases if f['is_hidden']]

                if visible_fails:
                    f = visible_fails[0]
                    feedback_message = (
                        f"❌ Неверный ответ.\n"
                        f"Ввод: {f['input'] or '(пусто)'}\n"
                        f"Ожидалось: {f['expected']}\n"
                        f"Получено: {f['actual']}"
                    )
                elif hidden_fails:
                    feedback_message = (
                        f"❌ Неверный ответ на скрытом тесте. "
                        f"Проверьте, что решение работает для любых значений, а не только для примера из условия."
                    )
        else:
            # Тест-кейсов нет — фолбэк на поле expected_output
            output = data.get('output', '')
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
            'task_completed': is_correct,
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
