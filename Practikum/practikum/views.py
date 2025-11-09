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

    # Получаем или создаём студента
    try:
        student = profile.student
    except Student.DoesNotExist:
        # Автоматически создаём студента для пользователя
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
