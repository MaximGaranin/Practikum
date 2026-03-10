from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField
from Logistic_Task.models import Course


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


class Teacher(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher',
        verbose_name='Преподаватель',
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
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'


class CourseTeacherGroup(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='Преподаватель')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курсы')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='Группы')
    start_date = models.DateField(auto_now_add=True, verbose_name='Дата начала')
    
    @property
    def students(self):
        return self.group.students.all()

    @property
    def students_count(self):
        """Количество студентов"""
        return self.group.students.count()

    class Meta:
        unique_together = [['teacher', 'course', 'group']]
        verbose_name = 'Назначение преподавателя'
        verbose_name_plural = 'Назначения преподавателей'
    
    def __str__(self):
        students_count = self.group.students.count()
        return f"{self.teacher} - {self.course.name} - {self.group.name} ({students_count} студентов)"

