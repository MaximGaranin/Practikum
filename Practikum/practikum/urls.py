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
    path('api/notifications/', views.notifications, name='notifications'),
    path('api/notifications/read/', views.mark_notifications_read, name='notifications_read'),
    path('contest/<int:contest_id>/', views.contest_detail, name='contest_detail'),

    # Маршруты для преподавателя
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),
    path('teacher/tasks/', views.teacher_tasks, name='teacher_tasks'),
    path('teacher/student/<int:student_id>/', views.teacher_student_detail, name='teacher_student_detail'),
    path('teacher/homework/assign/', views.teacher_assign_homework, name='teacher_assign_homework'),
    path('task/<int:task_id>/submit/', views.submit_solution, name='submit_solution'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),
    path('teacher/courses/create/', views.teacher_course_create, name='teacher_course_create'),
    path('teacher/courses/<int:course_id>/edit/', views.teacher_course_edit, name='teacher_course_edit'),
    path('teacher/courses/<int:course_id>/delete/', views.teacher_course_delete, name='teacher_course_delete'),
    path('teacher/tasks/', views.teacher_tasks, name='teacher_tasks'),
    path('teacher/tasks/create/', views.teacher_task_create, name='teacher_task_create'),
    path('teacher/tasks/<int:task_id>/edit/', views.teacher_task_edit, name='teacher_task_edit'),
    path('teacher/tasks/<int:task_id>/delete/', views.teacher_task_delete, name='teacher_task_delete'),
    path('teacher/topics/create/', views.teacher_topic_create, name='teacher_topic_create'),
    path('teacher/topics/<int:topic_id>/edit/', views.teacher_topic_edit, name='teacher_topic_edit'),
    path('teacher/topics/<int:topic_id>/delete/', views.teacher_topic_delete, name='teacher_topic_delete'),
    path('teacher/students/add/', views.teacher_add_student, name='teacher_add_student'),
]

