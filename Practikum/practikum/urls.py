from django.urls import path
from . import views

app_name = 'prac'

urlpatterns = [
    path('', views.course, name='course'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('task/', views.task, name='task'),
    path('settings/', views.settings, name='settings'),
    path('registration/', views.RegisterView.as_view(), name='register'),
    path('edit/<str:username>/', views.edit_profile, name='edit_profile'),
    
    # Маршруты для преподавателя
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),
    path('teacher/tasks/', views.teacher_tasks, name='teacher_tasks'),
    path('teacher/student/<int:student_id>/', views.teacher_student_detail, name='teacher_student_detail'),
]

