from django.shortcuts import render


def course(request):
    """Главная страница выбора курсов."""
    return render(request, 'course/course.html')


def course_program(request, course_id=None):
    """Страница программы курса."""
    # Генерируем 12 тем для примера
    topics = [{'id': i, 'name': f'Тема {i}'} for i in range(1, 13)]

    context = {
        'topics': topics,
        'course_id': course_id,
    }
    return render(request, 'course/course_program.html', context)


def profile(request):
    """Профиль."""
    return render(request, 'profile/profile.html')


def task(request):
    """Задачи."""
    return render(request, 'task/task.html')


def settings(request):
    """Настройки."""
    return render(request, 'settings/settings.html')