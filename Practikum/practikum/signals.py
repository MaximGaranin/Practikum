from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from Logistic_Task.models import Course
from .models import Student


@receiver(post_save, sender=User)
def create_student_and_enroll(sender, instance, created, **kwargs):
    """
    Автоматически создаёт профиль студента и записывает его
    в группу по умолчанию при регистрации пользователя.
    """
    if created:
        # Создаём профиль студента
        student = Student.objects.create(
            user=instance,
            first_name=instance.first_name if instance.first_name else 'Имя',
            last_name=instance.last_name if instance.last_name else 'Фамилия'
        )
        
        default_course, course_created = Course.objects.get_or_create(
            name='Базовый курс'
        )

        default_course.students.add(instance)
