from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'task_mananger'

urlpatterns = [
   path('course/<int:course_id>/', views.course_program, name='course_program'),
   path('course/<int:course_id>/task/<int:task_id>/', views.course_task, name='course_task'),]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
