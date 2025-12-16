from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def teacher_required(view_func):
    """
    Декоратор для проверки, что пользователь является преподавателем (staff).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо войти в систему')
            return redirect('login')
        
        if not request.user.is_staff:
            messages.error(request, 'Доступ запрещён. Только для преподавателей.')
            return redirect('prac:course')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
