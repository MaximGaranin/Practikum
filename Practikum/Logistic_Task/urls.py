from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'task_mananger'

urlpatterns = [
    path('course/<int:course_id>/', views.course_program, name='course_program'),
    path('course/<int:course_id>/task/<int:task_id>/', views.course_task, name='course_task'),
    path('api/analyze/', views.analyze_code, name='analyze_code'),
    path('api/execute/', views.execute_code, name='execute_code'),
    path('api/check/', views.check_task, name='check_task'),
    path('api/save/', views.save_code, name='save_code'),
    path('api/load/<int:task_id>/', views.load_saved_code, name='load_saved_code'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
