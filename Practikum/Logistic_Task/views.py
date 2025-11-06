from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from . import models


def course_program(request, course_id=None):
    course = get_object_or_404(models.Course, id=course_id)
    list_topic = course.topics.all()
    context = {
        'topics': list_topic,
        'course_id': course_id,
    }
    return render(request, 'course/course_program.html', context)


def course_task(request, course_program_id=None):
    task = get_object_or_404(models.Task, id=course_program_id)
    context = {
        'tasks': task,
        'course_program_id': course_program_id,
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
