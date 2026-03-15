import django
import pytest

@pytest.fixture
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_user(username='testuser', password='pass')

@pytest.fixture
def student(db, user):
    from practikum.models import Student
    return Student.objects.create(user=user, first_name='Иван', last_name='Иванов')
