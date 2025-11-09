from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField


class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student',
        verbose_name='Пользователь',
        null=True,
        blank=True
    )
    first_name = models.CharField(max_length=30, verbose_name='Имя', default='Имя')
    last_name = models.CharField(max_length=30, verbose_name='Фамилия', default='Фамилия')
    phone_number = PhoneNumberField(
        blank=True,
        null=True,
        region='RU',  # Код страны по умолчанию
        verbose_name='Телефон'
    )

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'


class Group(models.Model):
    name = models.CharField(max_length=30, default='group')
    students = models.ManyToManyField(Student, through='Enrollment')

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = [['student', 'group']]
