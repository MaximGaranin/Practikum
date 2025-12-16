from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.db.models import Count
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse, reverse_lazy
from .forms import UserEditForm
from Logistic_Task import models
from .models import Student, Group, Enrollment
from django.db.models import Count, Q
from django.http import JsonResponse
from .decorators import teacher_required

User = get_user_model()


def course(request):
    """Главная страница выбора курсов."""
    if request.user.is_authenticated:
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

    return render(request, 'profile/profile.html', context)


def task(request):
    """Задачи."""
    return render(request, 'task/task.html')


def settings(request):
    """Настройки."""
    return render(request, 'settings/settings.html')


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
    return render(request, 'registration/user.html', {'form': form})


@teacher_required
def teacher_dashboard(request):
    """Главная панель преподавателя."""
    from Logistic_Task.models import Course, Task
    
    # Статистика
    total_students = Student.objects.count()
    total_courses = Course.objects.count()
    total_tasks = Task.objects.count()
    total_groups = Group.objects.count()
    
    # Последние зарегистрированные студенты
    recent_students = Student.objects.select_related('user').order_by('-id')[:5]
    
    # Курсы с количеством студентов
    courses_stats = Course.objects.annotate(
        students_count=Count('students')
    ).order_by('-students_count')[:5]
    
    context = {
        'total_students': total_students,
        'total_courses': total_courses,
        'total_tasks': total_tasks,
        'total_groups': total_groups,
        'recent_students': recent_students,
        'courses_stats': courses_stats,
    }
    
    return render(request, 'teacher/dashboard.html', context)


@teacher_required
def teacher_students(request):
    """Управление студентами."""
    # Поиск
    search_query = request.GET.get('search', '')
    
    students_list = Student.objects.select_related('user').all()
    
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
    }
    
    return render(request, 'teacher/students.html', context)


@teacher_required
def teacher_courses(request):
    """Управление курсами."""
    from Logistic_Task.models import Course
    
    courses = Course.objects.annotate(
        students_count=Count('students'),
        topics_count=Count('topics')
    ).all()
    
    context = {
        'courses': courses,
    }
    
    return render(request, 'teacher/courses.html', context)


@teacher_required
def teacher_tasks(request):
    """Управление заданиями."""
    from Logistic_Task.models import Task, Topic
    
    tasks = Task.objects.all()
    topics = Topic.objects.annotate(tasks_count=Count('tasks')).all()
    
    context = {
        'tasks': tasks,
        'topics': topics,
    }
    
    return render(request, 'teacher/tasks.html', context)


@teacher_required
def teacher_student_detail(request, student_id):
    """Детальная информация о студенте."""
    student = get_object_or_404(Student, id=student_id)
    enrollments = Enrollment.objects.filter(student=student).select_related('group')
    courses = student.user.enrolled_courses.all()
    
    context = {
        'student': student,
        'enrollments': enrollments,
        'courses': courses,
    }
    
    return render(request, 'teacher/student_detail.html', context)
