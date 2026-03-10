from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField


class Task(models.Model):
    name = models.TextField()
    text_task = RichTextField(blank=True, null=True)
    initial_code = models.TextField(
        blank=True,
        default='# Напишите ваш код здесь\n',
        verbose_name='Начальный код'
    )
    expected_output = models.TextField(
        blank=True,
        null=True,
        verbose_name='Ожидаемый вывод'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
        ordering = ['order']

    def __str__(self):
        return self.name


class Topic(models.Model):
    name = models.TextField()
    image = models.ImageField(upload_to='topics/', blank=True, null=True)
    tasks = models.ManyToManyField(Task, blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы'
        ordering = ['order']

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.TextField()
    topics = models.ManyToManyField(Topic, blank=True)
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'

    def __str__(self):
        return self.name


class UserTaskProgress(models.Model):
    """Прогресс пользователя по задачам"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_progress')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='user_progress')
    code = models.TextField(blank=True, verbose_name='Последний код пользователя')
    is_completed = models.BooleanField(default=False, verbose_name='Выполнено')
    completed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0, verbose_name='Попыток')

    class Meta:
        unique_together = [['user', 'task']]
        verbose_name = 'Прогресс по заданию'
        verbose_name_plural = 'Прогресс по заданиям'

    def __str__(self):
        return f"{self.user.username} — {self.task.name}"

