from django.urls import path
from . import views

app_name = 'prac'

urlpatterns = [
    path('', views.course, name='course'),
    path('course/<int:course_id>/', views.course_program, name='course_program'),
    path('profile/', views.profile, name='profile'),
    path('task/', views.task, name='task'),
    path('settings/', views.settings, name='settings')
]
