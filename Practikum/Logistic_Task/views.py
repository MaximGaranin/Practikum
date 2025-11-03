from django.shortcuts import render, get_object_or_404
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
