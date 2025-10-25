from django.urls import path
from . import views

app_name = 'prac'

urlpatterns = [
    path('', views.curs, name='curs'),
]