from django.core.management.base import BaseCommand
from Logistic_Task.models import Task
from practikum.models import TestCase


# Каждый элемент: (task_name_contains, input, expected, is_hidden)
TEST_CASES = [
    # Задание 1: Приветствие
    ("Приветствие", "Максим", "Привет, Максим! Добро пожаловать в курс Python.", False),
    ("Приветствие", "Анна",   "Привет, Анна! Добро пожаловать в курс Python.", True),
    ("Приветствие", "Иван",   "Привет, Иван! Добро пожаловать в курс Python.", True),
    ("Приветствие", "test_user", "Привет, test_user! Добро пожаловать в курс Python.", True),

    # Задание 2: Визитка
    ("Визитка", "", "Меня зовут Максим, мне 25 лет, я живу в Москве.", False),
]


class Command(BaseCommand):
    help = 'Добавляет скрытые тест-кейсы для проверки заданий'

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0

        for task_name, inp, expected, is_hidden in TEST_CASES:
            tasks = Task.objects.filter(name__icontains=task_name)
            if not tasks.exists():
                self.stdout.write(self.style.WARNING(f'Задание «{task_name}» не найдено — пропуск.'))
                continue

            for task in tasks:
                exists = TestCase.objects.filter(
                    task=task, input=inp, expected=expected
                ).exists()
                if exists:
                    skipped_count += 1
                    continue
                TestCase.objects.create(
                    task=task,
                    input=inp,
                    expected=expected,
                    is_hidden=is_hidden,
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[✓] {task.name} | input=«{inp or "пусто"}» | hidden={is_hidden}'
                    )
                )

        self.stdout.write(f'\nГотово: создано {created_count}, пропущено {skipped_count} (уже существовало).')
