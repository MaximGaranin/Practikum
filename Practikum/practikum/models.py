from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField
from Logistic_Task.models import Course


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    text = models.TextField(verbose_name='Текст')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f"{self.user.username}: {self.text[:40]}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student', verbose_name='Пользователь', null=True, blank=True)
    first_name = models.CharField(max_length=30, verbose_name='Имя', default='Имя')
    last_name = models.CharField(max_length=30, verbose_name='Фамилия', default='Фамилия')
    phone_number = PhoneNumberField(blank=True, null=True, region='RU', verbose_name='Телефон')

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
        verbose_name = 'Количество учащихся'


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher', verbose_name='Преподаватель', null=True, blank=True)
    first_name = models.CharField(max_length=30, verbose_name='Имя', default='Имя')
    last_name = models.CharField(max_length=30, verbose_name='Фамилия', default='Фамилия')
    phone_number = PhoneNumberField(blank=True, null=True, region='RU', verbose_name='Телефон')

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
        return self.group.students.count()

    class Meta:
        unique_together = [['teacher', 'course', 'group']]
        verbose_name = 'Назначение преподавателя'
        verbose_name_plural = 'Назначения преподавателей'

    def __str__(self):
        return f"{self.teacher} - {self.course.name} - {self.group.name} ({self.group.students.count()} студентов)"


class Homework(models.Model):
    """ДЗ, назначенное преподавателем группе"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='Преподаватель')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='Группа')
    task = models.ForeignKey('Logistic_Task.Task', on_delete=models.CASCADE, verbose_name='Задание')
    deadline = models.DateTimeField(verbose_name='Дедлайн')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['group', 'task']]
        verbose_name = 'Домашнее задание'
        verbose_name_plural = 'Домашние задания'

    def __str__(self):
        return f"{self.group.name} — {self.task.name}"


class PersonalTask(models.Model):
    """Личная задача пользователя (не в группе)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_tasks')
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Дедлайн')
    is_completed = models.BooleanField(default=False, verbose_name='Выполнено')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Личная задача'
        verbose_name_plural = 'Личные задачи'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ===== ДОСТИЖЕНИЯ =====

class Achievement(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.CharField(max_length=255, verbose_name='Описание')
    icon = models.CharField(max_length=10, default='🏆', verbose_name='Иконка')
    condition_type = models.CharField(
        max_length=50,
        verbose_name='Тип условия',
        help_text='Например: solved_count или streak'
    )
    condition_value = models.IntegerField(default=1, verbose_name='Значение условия')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Достижение'
        verbose_name_plural = 'Достижения'

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')
        verbose_name = 'Достижение пользователя'
        verbose_name_plural = 'Достижения пользователей'


# ===== СОРЕВНОВАНИЯ =====
class Contest(models.Model):
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    tasks = models.ManyToManyField('Logistic_Task.Task', blank=True)  # ← исправлено

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Соревнование'
        verbose_name_plural = 'Соревнования'


class ContestScore(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    solved = models.IntegerField(default=0)

    class Meta:
        unique_together = ('contest', 'user')
        verbose_name = 'Результат соревнования'
        verbose_name_plural = 'Результаты соревнования'


# ===== КОД-РЕВЬЮ =====
class CodeReview(models.Model):
    STATUS = [
        ('pending', 'Ожидает'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    submission = models.ForeignKey('Submission', on_delete=models.CASCADE, related_name='reviews', verbose_name = 'Решение')
    reviewer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='reviews_given', verbose_name = 'Проверяющий')
    status = models.CharField(max_length=20, choices=STATUS, default='pending', verbose_name = 'Статус')
    comment = models.TextField(blank=True, verbose_name = 'Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Дата создания')

    class Meta:
        verbose_name = 'Код-ревью'
        verbose_name_plural = 'Код-ревью'


# ===== АВТОПРОВЕРКА (сабмиты) =====
class Submission(models.Model):
    STATUS = [
        ('accepted', 'Принято'),
        ('wrong_answer', 'Неверный ответ'),
        ('error', 'Ошибка'),
        ('pending', 'Ожидает'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    task = models.ForeignKey('Logistic_Task.Task', on_delete=models.CASCADE)  # ← исправлено
    code = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Решение'
        verbose_name_plural = 'Решения'


class TestCase(models.Model):
    task = models.ForeignKey('Logistic_Task.Task', on_delete=models.CASCADE, related_name='testcase_set')  # ← исправлено
    input = models.TextField()
    expected = models.TextField()
    is_hidden = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Тест-кейс'
        verbose_name_plural = 'Тест-кейсы'


# ===== ВАЛЮТА =====
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.IntegerField(default=0, verbose_name='Баланс')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.balance} монет"

    class Meta:
        verbose_name = 'Кошелёк'
        verbose_name_plural = 'Кошельки'


class Transaction(models.Model):
    TYPE = [
        ('task', 'За задачу'),
        ('first_try', 'Бонус за первую попытку'),
        ('achievement', 'За достижение'),
        ('contest', 'За соревнование'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.IntegerField(verbose_name='Сумма')
    type = models.CharField(max_length=20, choices=TYPE, verbose_name='Тип')
    description = models.CharField(max_length=255, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} +{self.amount} ({self.type})"
