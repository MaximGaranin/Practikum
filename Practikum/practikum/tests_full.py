"""
Полный набор тестов для проекта Practikum.
Покрывает: Checker, CodeAnalyzer, Wallet/Currency, Models, Signals, API, Views.
Запуск: pytest Practikum/practikum/tests_full.py -v
"""

import pytest
from mixer.backend.django import mixer
from django.contrib.auth.models import User
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.utils.timezone import now
from datetime import timedelta

from practikum.checker import is_code_safe, check_submission, is_complex_code
from practikum.currency import reward_for_task, reward_for_achievement, reward_for_contest, get_or_create_wallet
from practikum.models import (
    Wallet, Transaction, Achievement, UserAchievement,
    Enrollment, Student, Group, Teacher, CourseTeacherGroup,
    Notification, Homework, PersonalTask, Submission, TestCase as TC,
    CodeReview, Contest, ContestScore,
)
from Logistic_Task.models import Task, Topic, Course, UserTaskProgress


# ════════════════════════════════════════════════════════════════
# 1. ТЕМА: Checker (безопасность кода и проверка решений)
# ════════════════════════════════════════════════════════════════
class TestCheckerSafety:
    """Задача: проверка безопасности кода (is_code_safe)."""

    def test_safe_simple_code(self):
        assert is_code_safe('print("hello")') is True

    def test_safe_arithmetic(self):
        assert is_code_safe('x = 2 + 2\nprint(x)') is True

    def test_unsafe_import_os(self):
        assert is_code_safe('import os') is False

    def test_unsafe_import_sys(self):
        assert is_code_safe('import sys') is False

    def test_unsafe_import_subprocess(self):
        assert is_code_safe('import subprocess') is False

    def test_unsafe_eval(self):
        assert is_code_safe('eval("1+1")') is False

    def test_unsafe_exec(self):
        assert is_code_safe('exec("print(1)")') is False

    def test_unsafe_open(self):
        assert is_code_safe('open("file.txt")') is False

    def test_unsafe_dunder_import(self):
        assert is_code_safe('__import__("os")') is False

    def test_unsafe_from_os(self):
        assert is_code_safe('from os import path') is False

    def test_unsafe_requests(self):
        assert is_code_safe('import requests') is False

    def test_case_insensitive_check(self):
        # Проверяем нижний регистр (код приводится к lower)
        assert is_code_safe('Import Os') is False


class TestCheckerSubmission:
    """Задача: проверка решений задач (check_submission)."""

    def test_accepted_correct_code(self):
        code = 'print(int(input()) * 2)'
        cases = [{'input': '3', 'expected': '6'}]
        result = check_submission(code, cases)
        assert result['status'] == 'accepted'
        assert result['passed'] == 1
        assert result['total'] == 1

    def test_multiple_test_cases_all_pass(self):
        code = 'print(int(input()) + 1)'
        cases = [
            {'input': '0', 'expected': '1'},
            {'input': '9', 'expected': '10'},
            {'input': '-1', 'expected': '0'},
        ]
        result = check_submission(code, cases)
        assert result['status'] == 'accepted'
        assert result['passed'] == 3

    def test_wrong_answer(self):
        code = 'print(0)'
        cases = [{'input': '3', 'expected': '6'}]
        result = check_submission(code, cases)
        assert result['status'] == 'wrong_answer'
        assert result['passed'] == 0

    def test_partial_pass(self):
        code = 'x = int(input()); print(x * 2 if x > 0 else 0)'
        cases = [
            {'input': '3', 'expected': '6'},
            {'input': '-1', 'expected': '-2'},  # не пройдёт
        ]
        result = check_submission(code, cases)
        assert result['passed'] == 1
        assert result['total'] == 2

    def test_no_test_cases_returns_error(self):
        result = check_submission('print(1)', [])
        assert result['status'] == 'error'

    def test_unsafe_code_returns_error(self):
        result = check_submission('import os\nprint(os.getcwd())', [{'input': '', 'expected': ''}])
        assert result['status'] == 'error'
        assert 'запрещённые' in result.get('error', '')

    def test_results_list_has_correct_structure(self):
        code = 'print(int(input()) * 2)'
        cases = [{'input': '5', 'expected': '10'}]
        result = check_submission(code, cases)
        assert isinstance(result['results'], list)
        assert 'passed' in result['results'][0]
        assert 'expected' in result['results'][0]
        assert 'got' in result['results'][0]


class TestIsComplexCode:
    """Задача: определение сложности кода."""

    def test_simple_code_not_complex(self):
        code = 'x = 1\nprint(x)'
        assert is_complex_code(code) is False

    def test_heavy_library_is_complex(self):
        code = 'import numpy as np\nprint(np.array([1,2,3]))'
        assert is_complex_code(code) is True

    def test_pandas_is_complex(self):
        code = 'import pandas as pd'
        assert is_complex_code(code) is True

    def test_long_code_is_complex(self):
        lines = ['x = 1' for _ in range(60)]
        code = '\n'.join(lines)
        assert is_complex_code(code) is True


# ════════════════════════════════════════════════════════════════
# 2. ТЕМА: Wallet & Currency (начисление монет)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestWalletCreation:
    """Задача: автоматическое создание кошелька."""

    def test_wallet_created_on_reward(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Test task')
        assert Wallet.objects.filter(user=user).exists()

    def test_get_or_create_wallet(self):
        user = mixer.blend(User)
        wallet = get_or_create_wallet(user)
        assert wallet.user == user
        assert wallet.balance == 0

    def test_wallet_is_singleton(self):
        user = mixer.blend(User)
        w1 = get_or_create_wallet(user)
        w2 = get_or_create_wallet(user)
        assert w1.id == w2.id


@pytest.mark.django_db
class TestWalletBalance:
    """Задача: корректность начислений в кошелёк."""

    def test_task_reward_increases_balance(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance == 10  # REWARDS['task'] = 10

    def test_first_try_bonus_added(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1', is_first_try=True)
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance == 25  # 10 + 15

    def test_multiple_rewards_accumulate(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        reward_for_task(user, 'Задача 2')
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance == 20

    def test_achievement_reward(self):
        user = mixer.blend(User)
        reward_for_achievement(user, 'Первый шаг')
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance > 0

    def test_contest_reward(self):
        user = mixer.blend(User)
        reward_for_contest(user, 1, 100)
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance > 0


@pytest.mark.django_db
class TestTransactions:
    """Задача: создание транзакций при начислении."""

    def test_transaction_created_for_task(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        assert Transaction.objects.filter(user=user, type='task').exists()

    def test_transaction_type_first_try(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1', is_first_try=True)
        assert Transaction.objects.filter(user=user, type='first_try').exists()

    def test_transaction_amount_positive(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        tx = Transaction.objects.filter(user=user).first()
        assert tx.amount > 0

    def test_transaction_description_not_empty(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача X')
        tx = Transaction.objects.get(user=user, type='task')
        assert tx.description != ''


# ════════════════════════════════════════════════════════════════
# 3. ТЕМА: Модели (Task, Topic, Course, UserTaskProgress)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestTaskModel:
    """Задача: создание и свойства модели Task."""

    def test_task_creation(self):
        task = Task.objects.create(name='Задача 1', order=1)
        assert task.id is not None
        assert str(task) == 'Задача 1'

    def test_task_default_initial_code(self):
        task = Task.objects.create(name='Задача')
        assert '# Напишите ваш код здесь' in task.initial_code

    def test_task_ordering_by_order(self):
        Task.objects.create(name='B', order=2)
        Task.objects.create(name='A', order=1)
        tasks = list(Task.objects.all())
        assert tasks[0].name == 'A'
        assert tasks[1].name == 'B'


@pytest.mark.django_db
class TestTopicModel:
    """Задача: создание темы и добавление задач."""

    def test_topic_creation(self):
        topic = Topic.objects.create(name='Циклы')
        assert str(topic) == 'Циклы'

    def test_topic_with_tasks(self):
        task1 = Task.objects.create(name='Задача A')
        task2 = Task.objects.create(name='Задача B')
        topic = Topic.objects.create(name='Темa 1')
        topic.tasks.add(task1, task2)
        assert topic.tasks.count() == 2

    def test_topic_ordering(self):
        Topic.objects.create(name='Z', order=2)
        Topic.objects.create(name='A', order=1)
        topics = list(Topic.objects.all())
        assert topics[0].name == 'A'


@pytest.mark.django_db
class TestCourseModel:
    """Задача: создание курса и связи с темами."""

    def test_course_creation(self):
        course = Course.objects.create(name='Python Базовый')
        assert str(course) == 'Python Базовый'

    def test_course_with_topics(self):
        course = Course.objects.create(name='Курс 1')
        t1 = Topic.objects.create(name='Тема 1')
        t2 = Topic.objects.create(name='Тема 2')
        course.topics.add(t1, t2)
        assert course.topics.count() == 2

    def test_course_students_enrollment(self):
        course = Course.objects.create(name='Курс')
        user1 = mixer.blend(User)
        user2 = mixer.blend(User)
        course.students.add(user1, user2)
        assert course.students.count() == 2


@pytest.mark.django_db
class TestUserTaskProgress:
    """Задача: отслеживание прогресса пользователя по задачам."""

    def test_progress_creation(self):
        user = mixer.blend(User)
        task = Task.objects.create(name='Задача')
        progress = UserTaskProgress.objects.create(user=user, task=task)
        assert progress.is_completed is False
        assert progress.attempts == 0

    def test_unique_together_user_task(self):
        from django.db import IntegrityError
        user = mixer.blend(User)
        task = Task.objects.create(name='Задача')
        UserTaskProgress.objects.create(user=user, task=task)
        with pytest.raises(IntegrityError):
            UserTaskProgress.objects.create(user=user, task=task)

    def test_progress_str(self):
        user = mixer.blend(User)
        task = Task.objects.create(name='Задача X')
        progress = UserTaskProgress.objects.create(user=user, task=task)
        assert 'Задача X' in str(progress)


# ════════════════════════════════════════════════════════════════
# 4. ТЕМА: Студенты, Группы, Зачисление
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestStudentModel:
    """Задача: создание и свойства модели Student."""

    def test_student_str(self):
        student = mixer.blend(Student, first_name='Иван', last_name='Петров')
        assert 'Петров' in str(student)
        assert 'Иван' in str(student)

    def test_student_linked_to_user(self):
        user = mixer.blend(User)
        student = Student.objects.create(user=user, first_name='Анна', last_name='Сидорова')
        assert student.user == user


@pytest.mark.django_db
class TestGroupModel:
    """Задача: группы и зачисление студентов."""

    def test_group_creation(self):
        group = Group.objects.create(name='Группа А')
        assert str(group) == 'Группа А'

    def test_enrollment_student_in_group(self):
        student = mixer.blend(Student)
        group = mixer.blend(Group)
        enrollment = Enrollment.objects.create(student=student, group=group)
        assert enrollment.student == student
        assert enrollment.group == group

    def test_unique_enrollment(self):
        from django.db import IntegrityError
        student = mixer.blend(Student)
        group = mixer.blend(Group)
        Enrollment.objects.create(student=student, group=group)
        with pytest.raises(IntegrityError):
            Enrollment.objects.create(student=student, group=group)

    def test_group_students_through_enrollment(self):
        group = Group.objects.create(name='Группа B')
        s1 = mixer.blend(Student)
        s2 = mixer.blend(Student)
        Enrollment.objects.create(student=s1, group=group)
        Enrollment.objects.create(student=s2, group=group)
        assert group.students.count() == 2


# ════════════════════════════════════════════════════════════════
# 5. ТЕМА: Достижения (Achievements)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestAchievements:
    """Задача: выдача и дедупликация достижений."""

    def test_achievement_unlocked_on_solved_count(self):
        from practikum.views import _check_and_grant_achievements
        user = mixer.blend(User)
        ach = mixer.blend(Achievement, condition_type='solved_count', condition_value=1)
        _check_and_grant_achievements(user, total_solved=1, streak=0)
        assert UserAchievement.objects.filter(user=user, achievement=ach).exists()

    def test_achievement_not_unlocked_below_threshold(self):
        from practikum.views import _check_and_grant_achievements
        user = mixer.blend(User)
        mixer.blend(Achievement, condition_type='solved_count', condition_value=5)
        _check_and_grant_achievements(user, total_solved=3, streak=0)
        assert UserAchievement.objects.filter(user=user).count() == 0

    def test_no_duplicate_achievement(self):
        from practikum.views import _check_and_grant_achievements
        user = mixer.blend(User)
        ach = mixer.blend(Achievement, condition_type='solved_count', condition_value=1)
        _check_and_grant_achievements(user, total_solved=5, streak=0)
        _check_and_grant_achievements(user, total_solved=5, streak=0)
        assert UserAchievement.objects.filter(user=user, achievement=ach).count() == 1

    def test_streak_achievement(self):
        from practikum.views import _check_and_grant_achievements
        user = mixer.blend(User)
        ach = mixer.blend(Achievement, condition_type='streak', condition_value=3)
        _check_and_grant_achievements(user, total_solved=0, streak=5)
        assert UserAchievement.objects.filter(user=user, achievement=ach).exists()

    def test_achievement_str(self):
        ach = mixer.blend(Achievement, name='Первые шаги')
        assert str(ach) == 'Первые шаги'


# ════════════════════════════════════════════════════════════════
# 6. ТЕМА: Уведомления (Notifications) и Сигналы
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestNotifications:
    """Задача: создание уведомлений через сигналы и вручную."""

    def test_notification_created_manually(self):
        user = mixer.blend(User)
        Notification.objects.create(user=user, text='Тест')
        assert Notification.objects.filter(user=user).count() == 1

    def test_notification_default_is_read_false(self):
        user = mixer.blend(User)
        notif = Notification.objects.create(user=user, text='Новое уведомление')
        assert notif.is_read is False

    def test_notification_str(self):
        user = mixer.blend(User, username='testuser')
        notif = Notification.objects.create(user=user, text='Привет')
        assert 'testuser' in str(notif)

    def test_notification_on_code_review_approved(self):
        user = mixer.blend(User)
        sub = mixer.blend(Submission, user=user)
        review = mixer.blend(CodeReview, submission=sub, status='pending')
        review.status = 'approved'
        review.save()
        assert Notification.objects.filter(user=user).exists()

    def test_notification_on_code_review_rejected(self):
        user = mixer.blend(User)
        sub = mixer.blend(Submission, user=user)
        review = mixer.blend(CodeReview, submission=sub, status='pending')
        review.status = 'rejected'
        review.save()
        assert Notification.objects.filter(user=user).exists()


# ════════════════════════════════════════════════════════════════
# 7. ТЕМА: Личные задачи (PersonalTask)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestPersonalTask:
    """Задача: создание, выполнение и удаление личных задач."""

    def test_create_personal_task(self):
        user = mixer.blend(User)
        pt = PersonalTask.objects.create(user=user, title='Сделать задание')
        assert pt.is_completed is False
        assert str(pt) == 'Сделать задание'

    def test_complete_personal_task(self):
        user = mixer.blend(User)
        pt = PersonalTask.objects.create(user=user, title='Задача')
        PersonalTask.objects.filter(id=pt.id).update(is_completed=True)
        pt.refresh_from_db()
        assert pt.is_completed is True

    def test_personal_task_ordering_newest_first(self):
        user = mixer.blend(User)
        pt1 = PersonalTask.objects.create(user=user, title='Первая')
        pt2 = PersonalTask.objects.create(user=user, title='Вторая')
        tasks = list(PersonalTask.objects.filter(user=user))
        assert tasks[0].id == pt2.id  # ordering = ['-created_at']

    def test_personal_task_belongs_to_user(self):
        user = mixer.blend(User)
        other = mixer.blend(User)
        PersonalTask.objects.create(user=user, title='Моя задача')
        assert PersonalTask.objects.filter(user=other).count() == 0


# ════════════════════════════════════════════════════════════════
# 8. ТЕМА: Домашние задания (Homework)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestHomework:
    """Задача: назначение ДЗ группам."""

    def test_homework_creation(self):
        teacher = mixer.blend(Teacher)
        group = mixer.blend(Group)
        task = Task.objects.create(name='Задача ДЗ')
        deadline = now() + timedelta(days=7)
        hw = Homework.objects.create(teacher=teacher, group=group, task=task, deadline=deadline)
        assert 'Задача ДЗ' in str(hw)

    def test_homework_unique_per_group_task(self):
        from django.db import IntegrityError
        teacher = mixer.blend(Teacher)
        group = mixer.blend(Group)
        task = Task.objects.create(name='Уникальная задача')
        deadline = now() + timedelta(days=3)
        Homework.objects.create(teacher=teacher, group=group, task=task, deadline=deadline)
        with pytest.raises(IntegrityError):
            Homework.objects.create(teacher=teacher, group=group, task=task, deadline=deadline)


# ════════════════════════════════════════════════════════════════
# 9. ТЕМА: Соревнования (Contest & ContestScore)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestContest:
    """Задача: создание соревнований и регистрация участников."""

    def test_contest_creation(self):
        contest = Contest.objects.create(
            title='Олимпиада',
            start_time=now(),
            end_time=now() + timedelta(hours=2)
        )
        assert str(contest) == 'Олимпиада'

    def test_contest_score_default_zero(self):
        user = mixer.blend(User)
        contest = mixer.blend(Contest)
        score = ContestScore.objects.create(contest=contest, user=user)
        assert score.score == 0
        assert score.solved == 0

    def test_unique_contest_score_per_user(self):
        from django.db import IntegrityError
        user = mixer.blend(User)
        contest = mixer.blend(Contest)
        ContestScore.objects.create(contest=contest, user=user)
        with pytest.raises(IntegrityError):
            ContestScore.objects.create(contest=contest, user=user)

    def test_contest_score_increases(self):
        user = mixer.blend(User)
        contest = mixer.blend(Contest)
        score_obj = ContestScore.objects.create(contest=contest, user=user, score=0, solved=0)
        score_obj.score += 100
        score_obj.solved += 1
        score_obj.save()
        score_obj.refresh_from_db()
        assert score_obj.score == 100
        assert score_obj.solved == 1


# ════════════════════════════════════════════════════════════════
# 10. ТЕМА: Код-ревью (CodeReview)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestCodeReview:
    """Задача: создание и обновление статусов код-ревью."""

    def test_code_review_default_status_pending(self):
        sub = mixer.blend(Submission)
        review = CodeReview.objects.create(submission=sub)
        assert review.status == 'pending'

    def test_code_review_approve(self):
        sub = mixer.blend(Submission)
        review = CodeReview.objects.create(submission=sub)
        review.status = 'approved'
        review.save()
        review.refresh_from_db()
        assert review.status == 'approved'

    def test_code_review_reject(self):
        sub = mixer.blend(Submission)
        review = CodeReview.objects.create(submission=sub)
        review.status = 'rejected'
        review.save()
        review.refresh_from_db()
        assert review.status == 'rejected'


# ════════════════════════════════════════════════════════════════
# 11. ТЕМА: Тест-кейсы (TestCase)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestCaseModel:
    """Задача: создание тест-кейсов для задач."""

    def test_testcase_creation(self):
        task = Task.objects.create(name='Задача с тестами')
        tc = TC.objects.create(task=task, input='5', expected='10')
        assert tc.task == task
        assert tc.is_hidden is False

    def test_hidden_testcase(self):
        task = Task.objects.create(name='Задача')
        tc = TC.objects.create(task=task, input='1', expected='2', is_hidden=True)
        assert tc.is_hidden is True

    def test_testcase_linked_to_task(self):
        task = Task.objects.create(name='Задача')
        TC.objects.create(task=task, input='1', expected='1')
        TC.objects.create(task=task, input='2', expected='4')
        assert task.testcase_set.count() == 2


# ════════════════════════════════════════════════════════════════
# 12. ТЕМА: API соревнований (ContestListView, ContestDetailView и др.)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestContestAPI:
    """Задача: REST API для соревнований."""

    @pytest.fixture
    def client(self):
        from django.test import Client
        return Client()

    def test_contest_list_returns_200(self, client):
        response = client.get('/api/contests/')
        assert response.status_code == 200

    def test_contest_list_empty(self, client):
        response = client.get('/api/contests/')
        assert response.json() == []

    def test_contest_list_with_data(self, client):
        Contest.objects.create(
            title='Тест API',
            start_time=now(),
            end_time=now() + timedelta(hours=1)
        )
        response = client.get('/api/contests/')
        data = response.json()
        assert len(data) == 1
        assert data[0]['title'] == 'Тест API'

    def test_contest_detail_returns_200(self, client):
        contest = Contest.objects.create(
            title='Детали',
            start_time=now(),
            end_time=now() + timedelta(hours=1)
        )
        response = client.get(f'/api/contests/{contest.id}/')
        assert response.status_code == 200

    def test_contest_detail_not_found_returns_404(self, client):
        response = client.get('/api/contests/99999/')
        assert response.status_code == 404

    def test_contest_register_requires_auth(self, client):
        contest = Contest.objects.create(
            title='Закрытый',
            start_time=now(),
            end_time=now() + timedelta(hours=1)
        )
        response = client.post(f'/api/contests/{contest.id}/register/')
        assert response.status_code in [401, 403]

    def test_contest_leaderboard_returns_200(self, client):
        contest = Contest.objects.create(
            title='Лидеры',
            start_time=now(),
            end_time=now() + timedelta(hours=1)
        )
        response = client.get(f'/api/contests/{contest.id}/leaderboard/')
        assert response.status_code == 200

    def test_contest_is_active_field(self, client):
        Contest.objects.create(
            title='Активный',
            start_time=now() - timedelta(minutes=1),
            end_time=now() + timedelta(hours=1)
        )
        response = client.get('/api/contests/')
        data = response.json()
        assert data[0]['is_active'] is True

    def test_contest_is_inactive_field(self, client):
        Contest.objects.create(
            title='Прошедший',
            start_time=now() - timedelta(hours=2),
            end_time=now() - timedelta(hours=1)
        )
        response = client.get('/api/contests/')
        data = response.json()
        assert data[0]['is_active'] is False


# ════════════════════════════════════════════════════════════════
# 13. ТЕМА: Views (submit_solution, task, notifications)
# ════════════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestSubmitSolutionView:
    """Задача: представление submit_solution."""

    @pytest.fixture
    def auth_client(self):
        client = Client()
        user = User.objects.create_user(username='student', password='pass123')
        client.login(username='student', password='pass123')
        return client, user

    def test_submit_requires_post(self, auth_client):
        client, _ = auth_client
        task = Task.objects.create(name='Задача')
        response = client.get(f'/prac/submit/{task.id}/')
        assert response.status_code == 405

    def test_submit_accepted(self, auth_client):
        client, user = auth_client
        task = Task.objects.create(name='Задача')
        TC.objects.create(task=task, input='2', expected='4')
        response = client.post(
            f'/prac/submit/{task.id}/',
            data={'code': 'print(int(input()) * 2)'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'accepted'

    def test_submit_creates_submission_record(self, auth_client):
        client, user = auth_client
        task = Task.objects.create(name='Задача')
        TC.objects.create(task=task, input='1', expected='1')
        client.post(f'/prac/submit/{task.id}/', data={'code': 'print(input())'})
        assert Submission.objects.filter(user=user, task=task).exists()

    def test_submit_wrong_answer_no_reward(self, auth_client):
        client, user = auth_client
        task = Task.objects.create(name='Задача')
        TC.objects.create(task=task, input='1', expected='999')
        client.post(f'/prac/submit/{task.id}/', data={'code': 'print(0)'})
        assert not Wallet.objects.filter(user=user).exists()

    def test_submit_accepted_creates_wallet(self, auth_client):
        client, user = auth_client
        task = Task.objects.create(name='Задача')
        TC.objects.create(task=task, input='2', expected='4')
        client.post(f'/prac/submit/{task.id}/', data={'code': 'print(int(input()) * 2)'})
        assert Wallet.objects.filter(user=user).exists()

    def test_submit_unauthenticated_redirects(self):
        client = Client()
        task = Task.objects.create(name='Задача')
        response = client.post(f'/prac/submit/{task.id}/', data={'code': 'print(1)'})
        assert response.status_code in [302, 403]


@pytest.mark.django_db
class TestNotificationsView:
    """Задача: API для уведомлений."""

    def test_notifications_requires_auth(self):
        client = Client()
        response = client.get('/prac/notifications/')
        assert response.status_code == 302  # redirect to login

    def test_notifications_returns_json(self):
        client = Client()
        user = User.objects.create_user(username='notif_user', password='pass')
        client.login(username='notif_user', password='pass')
        Notification.objects.create(user=user, text='Тест уведомление')
        response = client.get('/prac/notifications/')
        assert response.status_code == 200
        data = response.json()
        assert 'notifications' in data
        assert 'count' in data

    def test_mark_notifications_read(self):
        client = Client()
        user = User.objects.create_user(username='mark_user', password='pass')
        client.login(username='mark_user', password='pass')
        Notification.objects.create(user=user, text='Непрочитанное')
        response = client.post('/prac/notifications/read/')
        assert response.status_code == 200
        assert Notification.objects.filter(user=user, is_read=False).count() == 0
