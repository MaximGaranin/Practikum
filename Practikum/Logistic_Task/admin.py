from django.contrib import admin
from .models import Course, Topic, Task

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_students_count']
    filter_horizontal = ['topics', 'students']

    def get_students_count(self, obj):
        return obj.students.count()
    get_students_count.short_description = 'Студентов'

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'image']
    fields = ['name', 'image', 'tasks']
    filter_horizontal = ['tasks']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'text_task']
