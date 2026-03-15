from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from Logistic_Task.models import Course
from .models import Student
from .models import Notification
from django.contrib.auth import get_user_model


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


@receiver(post_save, sender='practikum.CodeReview')
def notify_on_code_review(sender, instance, created, **kwargs):
    """Уведомить студента при изменении статуса код-ревью."""
    from .models import Notification, CodeReview
    # Уведомляем только при смене статуса (не при создании в 'pending')
    if not created and instance.status in ('approved', 'rejected'):
        icon = '✅' if instance.status == 'approved' else '❌'
        status_text = 'одобрено' if instance.status == 'approved' else 'отклонено'
        task_name = instance.submission.task.name
        Notification.objects.create(
            user=instance.submission.user,
            text=f'{icon} Ревью {status_text}: «{task_name}»'
        )


@receiver(post_save, sender='practikum.Contest')
def notify_on_new_contest(sender, instance, created, **kwargs):
    """Уведомить всех активных пользователей о новом соревновании."""
    User = get_user_model()
    if created:
        users = User.objects.filter(is_active=True)
        notifications = [
            Notification(
                user=user,
                text=f'🏆 Новое соревнование: «{instance.title}» — начало {instance.start_time.strftime("%d.%m %H:%M")}'
            )
            for user in users
        ]
        Notification.objects.bulk_create(notifications)
