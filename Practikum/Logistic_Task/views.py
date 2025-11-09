from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from . import models


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

    # Находим номер текущей задачи
    task_number = 0
    for i, t in enumerate(all_tasks, 1):
        if t.id == task.id:
            task_number = i
            break

    context = {
        'task': task,
        'task_text': task.text_task,
        'task_id': task_id,
        'course': course,
        'course_id': course_id,
        'topic': topic,
        'task_number': task_number,  # Добавлено
        'next_task': task_number + 1,
        'previous_task': task_number - 1,
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
