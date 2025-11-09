from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField

class Task(models.Model):
    name = models.TextField()
    text_task = RichTextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'


class Topic(models.Model):
    name = models.TextField()
    image = models.ImageField(upload_to='topics/', blank=True, null=True)
    tasks = models.ManyToManyField(Task)

    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы'


class Course(models.Model):
    name = models.TextField()
    topics = models.ManyToManyField(Topic)
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
