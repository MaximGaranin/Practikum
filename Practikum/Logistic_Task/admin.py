from django.contrib import admin
from .models import Course, Topic, Task

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    filter_horizontal = ['topics']

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    filter_horizontal = ['tasks']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'text_task']
