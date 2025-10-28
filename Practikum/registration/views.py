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


User = get_user_model()


def profile(request, username):
    """Страница профиля пользователя."""
    profile_user = get_object_or_404(User, username=username)
    return render(request, 'profile/profile.html', {'profile': profile_user})


@login_required
def edit_profile(request, username):
    """Редактирование профиля."""
    user = get_object_or_404(User, username=username)

    if request.user != user:
        return redirect('reg:profile', username=username)

    form = UserEditForm(request.POST or None, instance=user)

    if form.is_valid():
        form.save()
        return redirect('reg:profile', username=username)

    return render(request, 'registration/user.html', {'form': form})

class RegisterView(CreateView):
    """Регистрация пользователя."""

    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('prac:course')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)
