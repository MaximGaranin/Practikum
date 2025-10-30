from django.shortcuts import render
from . import models

# Create your views here.
def course_program(request, course_id=None):
    m1 = models.Course(name="name")
    m2 = models.Course(name="name")
    m3 = models.Course(name="name")
    m1.save()
    m2.save()
    m3.save()
    course = models.Course.objects.get(id=course_id)
    list_topic = course.topics
    context = {
        'topics': list_topic,
        'course_id': course_id,
    }
    return render(request, 'course/course_program.html', context)