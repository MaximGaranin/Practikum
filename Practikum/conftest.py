import django
import pytest
from django.conf import settings


def pytest_configure():
    """Вызывается pytest до сбора тестов — настраиваем Django."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )


@pytest.fixture
def student(db, user):
    from practikum.models import Student
    return Student.objects.get_or_create(
        user=user,
        defaults={'first_name': 'Иван', 'last_name': 'Иванов'}
    )[0]


@pytest.fixture
def teacher_user(db):
    from django.contrib.auth.models import User
    from practikum.models import Teacher
    u = User.objects.create_user(username='teacher', password='pass')
    Teacher.objects.create(user=u, first_name='Пётр', last_name='Петров')
    return u


@pytest.fixture
def client_logged(client, user):
    """Django test client с залогиненным пользователем."""
    client.login(username='testuser', password='testpass123')
    return client
