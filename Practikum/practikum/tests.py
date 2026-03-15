import pytest
from mixer.backend.django import mixer
from django.contrib.auth.models import User

from practikum.checker import is_code_safe, check_submission
from practikum.currency import reward_for_task, get_or_create_wallet
from practikum.models import (
    Wallet, Transaction, Achievement, UserAchievement,
    Enrollment, Student, Group, Notification, Homework
)
from editor.code_analyzer import CodeAnalyzer


# ── Checker ────────────────────────────────────────────────────
class TestChecker:
    def test_safe_code(self):
        assert is_code_safe('print("hello")') is True

    def test_unsafe_import_os(self):
        assert is_code_safe('import os') is False

    def test_unsafe_eval(self):
        assert is_code_safe('eval("1+1")') is False

    def test_submission_accepted(self):
        code = 'print(int(input()) * 2)'
        test_cases = [{'input': '3', 'expected': '6'}]
        result = check_submission(code, test_cases)
        assert result['status'] == 'accepted'
        assert result['passed'] == 1

    def test_submission_wrong_answer(self):
        code = 'print(0)'
        test_cases = [{'input': '3', 'expected': '6'}]
        result = check_submission(code, test_cases)
        assert result['status'] == 'wrong_answer'

    def test_no_test_cases(self):
        result = check_submission('print(1)', [])
        assert result['status'] == 'error'


# ── CodeAnalyzer (локально vs сервер) ─────────────────────────
class TestCodeAnalyzer:
    def test_simple_code_is_client(self):
        code = 'x = 1\nprint(x)'
        result = CodeAnalyzer(code).analyze()
        assert result['execution_mode'] == 'client'

    def test_os_import_is_server(self):
        code = 'import os\nprint(os.getcwd())'
        result = CodeAnalyzer(code).analyze()
        assert result['execution_mode'] == 'server'

    def test_syntax_error_is_server(self):
        code = 'def foo(:\n    pass'
        result = CodeAnalyzer(code).analyze()
        assert result['execution_mode'] == 'server'


# ── Wallet & Currency ─────────────────────────────────────────
@pytest.mark.django_db
class TestWallet:
    def test_wallet_created_on_reward(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        assert Wallet.objects.filter(user=user).exists()

    def test_balance_increases(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance == 10  # REWARDS['task'] = 10

    def test_first_try_bonus(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1', is_first_try=True)
        wallet = Wallet.objects.get(user=user)
        assert wallet.balance == 25  # 10 + 15

    def test_transaction_created(self):
        user = mixer.blend(User)
        reward_for_task(user, 'Задача 1')
        assert Transaction.objects.filter(user=user, type='task').exists()


# ── Achievements ──────────────────────────────────────────────
@pytest.mark.django_db
class TestAchievements:
    def test_achievement_unlocked(self):
        user = mixer.blend(User)
        ach = mixer.blend(Achievement, condition_type='solved_count', condition_value=1)
        from practikum.views import _check_and_grant_achievements
        _check_and_grant_achievements(user, total_solved=1, streak=0)
        assert UserAchievement.objects.filter(user=user, achievement=ach).exists()

    def test_no_duplicate_achievement(self):
        user = mixer.blend(User)
        ach = mixer.blend(Achievement, condition_type='solved_count', condition_value=1)
        from practikum.views import _check_and_grant_achievements
        _check_and_grant_achievements(user, total_solved=5, streak=0)
        _check_and_grant_achievements(user, total_solved=5, streak=0)
        assert UserAchievement.objects.filter(user=user, achievement=ach).count() == 1


# ── Enrollment ────────────────────────────────────────────────
@pytest.mark.django_db
class TestEnrollment:
    def test_unique_enrollment(self):
        from django.db import IntegrityError
        student = mixer.blend(Student)
        group = mixer.blend(Group)
        Enrollment.objects.create(student=student, group=group)
        with pytest.raises(IntegrityError):
            Enrollment.objects.create(student=student, group=group)


# ── Signals / Notifications ───────────────────────────────────
@pytest.mark.django_db
class TestNotifications:
    def test_notification_on_code_review_approved(self):
        from practikum.models import CodeReview, Submission
        user = mixer.blend(User)
        sub = mixer.blend(Submission, user=user)
        review = mixer.blend(CodeReview, submission=sub, status='pending')
        # Меняем статус → сигнал должен создать уведомление
        review.status = 'approved'
        review.save()
        assert Notification.objects.filter(user=user).exists()

