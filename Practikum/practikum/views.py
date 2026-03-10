from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse, reverse_lazy
from .forms import UserEditForm
from Logistic_Task.models import Course, Topic, Task
from .models import Student, Group, Enrollment, Teacher, CourseTeacherGroup
from django.http import JsonResponse
from .decorators import teacher_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

User = get_user_model()

def course(request):
    """Главная страница выбора курсов."""
    if request.user.is_authenticated:
        if hasattr(request.user, 'teacher'):
            return redirect('prac:teacher_dashboard')

        courses = request.user.enrolled_courses.all()
        context = {
                'courses': courses,
                'user': request.user
            }
        return render(request, 'course/course.html', context)
    else:
        return render(request, 'course/course.html')


def profile(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username)
    else:
        profile = request.user

    # Получаем студента (он должен существовать благодаря сигналу)
    try:
        student = profile.student
    except Student.DoesNotExist:
        # На всякий случай создаём, если не создался через сигнал
        student = Student.objects.create(
            user=profile,
            first_name=profile.first_name,
            last_name=profile.last_name
        )

    enrollment = Enrollment.objects.filter(student=student).first()
    group = enrollment.group if enrollment else None

    if request.method == 'POST' and request.user == profile:
        profile.first_name = request.POST.get('first_name', '').strip()
        profile.last_name = request.POST.get('last_name', '').strip()
        profile.email = request.POST.get('email', '').strip()
        profile.save()

        student.first_name = profile.first_name
        student.last_name = profile.last_name
        student.phone_number = request.POST.get('phone_number', '').strip()
        student.save()

    context = {
        'profile': profile,
        'student': student,
        'group': group,
    }

    if hasattr(request.user, 'teacher'):
        return render(request, 'teacher/profile.html', context)
    else:
        return render(request, 'profile/profile.html', context)


@login_required
def task(request):
    """Страница ДЗ пользователя."""
    from Logistic_Task.models import Task, UserTaskProgress

    # Все задачи из курсов пользователя
    user_courses = request.user.enrolled_courses.all()
    all_tasks = Task.objects.filter(
        topic__course__in=user_courses
    ).distinct()

    # Прогресс пользователя
    progress_qs = UserTaskProgress.objects.filter(
        user=request.user,
        task__in=all_tasks
    ).select_related('task')
    progress_map = {p.task_id: p for p in progress_qs}

    # Собираем итоговый список
    tasks_data = []
    for t in all_tasks:
        progress = progress_map.get(t.id)
        tasks_data.append({
            'task': t,
            'is_completed': progress.is_completed if progress else False,
            'attempts': progress.attempts if progress else 0,
            'completed_at': progress.completed_at if progress else None,
        })

    total = len(tasks_data)
    completed = sum(1 for t in tasks_data if t['is_completed'])
    in_progress = sum(1 for t in tasks_data if t['attempts'] > 0 and not t['is_completed'])

    context = {
        'tasks_data': tasks_data,
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
    }
    return render(request, 'task/task.html', context)


@login_required
def settings(request):
    user = request.user
    password_error = None
    password_success = None
    delete_error = None

    if request.method == 'POST':
        action = request.POST.get('action')

        # Смена пароля
        if action == 'change_password':
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                password_success = 'Пароль успешно изменён'
            else:
                password_error = ' '.join(
                    [e for errors in form.errors.values() for e in errors]
                )

        # Удаление аккаунта
        elif action == 'delete_account':
            confirm = request.POST.get('confirm_delete')
            if confirm == 'DELETE':
                user.delete()
                from django.contrib.auth import logout
                logout(request)
                return redirect('prac:course')
            else:
                delete_error = 'Введите DELETE для подтверждения'

    context = {
        'password_error': password_error,
        'password_success': password_success,
        'delete_error': delete_error,
    }
    return render(request, 'settings/settings.html', context)


class RegisterView(CreateView):
    """Регистрация пользователя."""

    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('prac:course')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


@login_required
def edit_profile(request, username):
    """Редактирование профиля."""
    user = get_object_or_404(User, username=username)

    if request.user != user:
        return redirect('prac:profile', username=username)

    form = UserEditForm(request.POST or None, instance=user)

    if form.is_valid():
        form.save()
        return redirect('prac:profile', username=username)

    return render(request, 'registration/user.html', {'form': form})


@teacher_required
def teacher_dashboard(request):
    """Главная панель преподавателя."""
    
    # Получаем текущего преподавателя
    teacher = request.user.teacher
    
    # Получаем все назначения этого преподавателя
    teacher_assignments = CourseTeacherGroup.objects.filter(teacher=teacher)
    
    # ID групп, курсов преподавателя
    teacher_groups = teacher_assignments.values_list('group', flat=True)
    teacher_courses = teacher_assignments.values_list('course', flat=True)
    
    # Статистика только по группам преподавателя
    total_students = Student.objects.filter(
        enrollment__group__id__in=teacher_groups
    ).distinct().count()
    
    total_courses = Course.objects.filter(id__in=teacher_courses).count()
    total_groups = Group.objects.filter(id__in=teacher_groups).count()
    
    # Задания из курсов преподавателя
    total_tasks = Task.objects.filter(
        topic__course__id__in=teacher_courses
    ).distinct().count()
    
    # Последние студенты из групп преподавателя
    recent_students = Student.objects.filter(
        enrollment__group__id__in=teacher_groups
    ).distinct().select_related('user').order_by('-id')[:5]
    
    # Курсы преподавателя с количеством студентов
    courses_stats = Course.objects.filter(
        id__in=teacher_courses
    ).annotate(
        students_count=Count('students', distinct=True)
    ).order_by('-students_count')[:5]
    
    context = {
        'total_students': total_students,
        'total_courses': total_courses,
        'total_tasks': total_tasks,
        'total_groups': total_groups,
        'recent_students': recent_students,
        'courses_stats': courses_stats,
        'teacher': teacher,
    }
    
    return render(request, 'teacher/dashboard.html', context)


@teacher_required
def teacher_students(request):
    """Управление студентами преподавателя."""
    teacher = request.user.teacher
    
    # Группы преподавателя
    teacher_groups = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('group', flat=True)
    
    # Поиск
    search_query = request.GET.get('search', '')
    
    # Только студенты из групп преподавателя
    students_list = Student.objects.filter(
        enrollment__group__id__in=teacher_groups
    ).distinct().select_related('user')
    
    if search_query:
        students_list = students_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(students_list, 20)
    page_number = request.GET.get('page', 1)
    students = paginator.get_page(page_number)
    
    context = {
        'students': students,
        'search_query': search_query,
        'teacher': teacher,
    }
    
    return render(request, 'teacher/students.html', context)


@teacher_required
def teacher_courses(request):
    """Управление курсами преподавателя."""
    teacher = request.user.teacher
    
    # Курсы преподавателя
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()
    
    courses = Course.objects.filter(
        id__in=teacher_courses_ids
    ).annotate(
        students_count=Count('students', distinct=True),
        topics_count=Count('topics', distinct=True)
    )
    
    context = {
        'courses': courses,
        'teacher': teacher,
    }
    
    return render(request, 'teacher/courses.html', context)


@teacher_required
def teacher_tasks(request):
    """Управление заданиями из курсов преподавателя."""
    from Logistic_Task.models import Course, Topic, Task
    
    teacher = request.user.teacher
    
    # Курсы преподавателя
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()
    
    # Задания только из курсов преподавателя
    tasks = Task.objects.filter(
        topic__course__id__in=teacher_courses_ids
    ).distinct()
    
    # Темы из курсов преподавателя
    topics = Topic.objects.filter(
        course__id__in=teacher_courses_ids
    ).annotate(
        tasks_count=Count('tasks')
    ).distinct()
    
    context = {
        'tasks': tasks,
        'topics': topics,
        'teacher': teacher,
    }
    
    return render(request, 'teacher/tasks.html', context)


@teacher_required
def teacher_student_detail(request, student_id):
    """Детальная информация о студенте (только из групп преподавателя)."""
    teacher = request.user.teacher
    
    # Группы преподавателя
    teacher_groups = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('group', flat=True)
    
    # Студент должен быть в группах преподавателя
    student = get_object_or_404(
        Student,
        id=student_id,
        enrollment__group__id__in=teacher_groups
    )
    
    enrollments = Enrollment.objects.filter(
        student=student,
        group__id__in=teacher_groups
    ).select_related('group')
    
    # Курсы преподавателя, на которые записан студент
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True)
    
    courses = student.user.enrolled_courses.filter(
        id__in=teacher_courses_ids
    )
    
    context = {
        'student': student,
        'enrollments': enrollments,
        'courses': courses,
        'teacher': teacher,
    }
    
    return render(request, 'teacher/student_detail.html', context)
