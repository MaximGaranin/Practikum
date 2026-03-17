from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.db.models import Count, Q, Sum, Prefetch
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse, reverse_lazy
from .forms import UserEditForm
from Logistic_Task.models import Course, Topic, Task, UserTaskProgress
from .models import Student, Group, Enrollment, Teacher, CourseTeacherGroup, Homework, PersonalTask, Notification, Achievement, UserAchievement, Contest, ContestScore, CodeReview, Submission
from django.http import JsonResponse
from .decorators import teacher_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import json
from django.contrib import messages
from datetime import date, timedelta
from django.db import models as django_models_db
from .checker import check_submission
from django.utils.timezone import now as tz_now
from .currency import reward_for_task, reward_for_achievement, reward_for_contest, get_or_create_wallet
from .forms import AddStudentForm
from datetime import date, timedelta

User = get_user_model()

@login_required
def notifications(request):
    from .models import Notification
    notifs = Notification.objects.filter(user=request.user, is_read=False)[:10]
    data = [{'id': n.id, 'text': n.text, 'created_at': n.created_at.strftime('%d.%m %H:%M')} for n in notifs]
    return JsonResponse({'notifications': data, 'count': notifs.count()})

@login_required  
def mark_notifications_read(request):
    from .models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


def course(request):
    if request.user.is_authenticated:
        try:
            _ = request.user.teacher
            return redirect('prac:teacher_dashboard')
        except:
            pass

    all_courses = Course.objects.all()

    in_group = False
    if request.user.is_authenticated:
        try:
            student = request.user.student
            in_group = Enrollment.objects.filter(student=student).exists()
        except:
            in_group = False

    courses_data = []
    for c in all_courses:
        is_locked = not in_group and c.name != 'Базовый курс'

        progress_percent = 0
        if request.user.is_authenticated and not is_locked:
            total_tasks = Task.objects.filter(
                topic__course=c
            ).distinct().count()

            if total_tasks > 0:
                completed = UserTaskProgress.objects.filter(
                    user=request.user,
                    task__topic__course=c,
                    is_completed=True
                ).count()
                progress_percent = round((completed / total_tasks) * 100)

        courses_data.append({
            'course': c,
            'progress': progress_percent,
            'topics_count': c.topics.count(),
            'students_count': c.students.count(),
            'is_locked': is_locked,
        })

    context = {
        'courses': courses_data,
        'in_group': in_group,
    }
    return render(request, 'course/course.html', context)


def _check_and_grant_achievements(user, total_solved, streak):
    rules = [
        ('solved_count', total_solved),
        ('streak', streak),
    ]
    for condition_type, value in rules:
        qs = Achievement.objects.filter(
            condition_type=condition_type,
            condition_value__lte=value
        )
        for ach in qs:
            _, created = UserAchievement.objects.get_or_create(
                user=user, achievement=ach
            )
            if created:
                reward_for_achievement(user, ach.name)


def profile(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username)
    else:
        profile = request.user

    try:
        student = profile.student
    except Student.DoesNotExist:
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

    one_year_ago = now() - timedelta(days=365)
    completions = UserTaskProgress.objects.filter(
        user=profile,
        is_completed=True,
        completed_at__gte=one_year_ago
    ).values_list('completed_at', flat=True)

    activity_map = {}
    for dt in completions:
        day_str = dt.strftime('%Y-%m-%d')
        activity_map[day_str] = activity_map.get(day_str, 0) + 1

    total_solved = UserTaskProgress.objects.filter(user=profile, is_completed=True).count()
    total_attempts = UserTaskProgress.objects.filter(user=profile).aggregate(
        total=Sum('attempts')
    )['total'] or 0
    courses_count = profile.enrolled_courses.count()

    streak = 0
    today = date.today()
    for i in range(365):
        day = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        if activity_map.get(day, 0) > 0:
            streak += 1
        else:
            break

    all_achievements = Achievement.objects.all()
    unlocked_ids = set(
        UserAchievement.objects.filter(user=profile).values_list('achievement_id', flat=True)
    )
    achievements = [
        {
            'icon': ach.icon,
            'name': ach.name,
            'description': ach.description,
            'unlocked': ach.id in unlocked_ids,
        }
        for ach in all_achievements
    ]

    if request.user == profile:
        _check_and_grant_achievements(profile, total_solved, streak)

    current_time = now()
    active_contests = Contest.objects.filter(
        start_time__lte=current_time,
        end_time__gte=current_time
    ).prefetch_related('tasks')

    past_contests = Contest.objects.filter(
        end_time__lt=current_time
    ).prefetch_related('tasks').order_by('-end_time')[:5]

    past_contests_with_rank = []
    for contest in past_contests:
        scores = list(
            ContestScore.objects.filter(contest=contest).order_by('-score')
        )
        rank = None
        for i, s in enumerate(scores, 1):
            if s.user == profile:
                rank = i
                break
        past_contests_with_rank.append({'contest': contest, 'rank': rank})

    reviews = (
        CodeReview.objects
        .filter(submission__user=profile)
        .select_related('submission__task', 'reviewer')
        .order_by('-created_at')[:10]
    )

    wallet = get_or_create_wallet(profile)
    transactions = profile.transactions.all()[:10]

    context = {
        'profile': profile,
        'student': student,
        'group': group,
        'phone_number': student.phone_number,
        'activity_map': json.dumps(activity_map),
        'total_solved': total_solved,
        'total_attempts': total_attempts,
        'courses_count': courses_count,
        'streak': streak,
        'achievements': achievements,
        'active_contests': active_contests,
        'past_contests_with_rank': past_contests_with_rank,
        'reviews': reviews,
        'wallet': wallet,
        'transactions': transactions,
    }

    if hasattr(request.user, 'teacher'):
        return render(request, 'teacher/profile.html', context)
    else:
        return render(request, 'profile/profile.html', context)


@login_required
def submit_solution(request, task_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    task = get_object_or_404(Task, id=task_id)
    code = request.POST.get('code', '')

    # Загружаем все тест-кейсы с флагом is_hidden
    all_test_cases = list(task.testcase_set.values('input', 'expected', 'is_hidden'))

    # Для проверки используем ВСЕ тест-кейсы (включая скрытые)
    test_cases_for_checker = [
        {'input': tc['input'], 'expected': tc['expected']}
        for tc in all_test_cases
    ]
    result = check_submission(code, test_cases_for_checker)

    # Для ответа студенту — скрываем input/expected скрытых тест-кейсов
    safe_results = []
    for i, (res, tc) in enumerate(zip(result.get('results', []), all_test_cases)):
        if tc['is_hidden']:
            safe_results.append({
                'test': res['test'],
                'passed': res['passed'],
                'expected': '*** скрыто ***',
                'got': res['got'] if not res['passed'] else '*** скрыто ***',
                'error': res.get('error', ''),
                'is_hidden': True,
            })
        else:
            safe_results.append({**res, 'is_hidden': False})

    # Считаем попытки до этого
    previous_attempts = Submission.objects.filter(
        user=request.user, task=task
    ).count()

    Submission.objects.create(
        user=request.user,
        task=task,
        code=code,
        status=result['status'],
    )

    if result['status'] == 'accepted':
        is_first_try = previous_attempts == 0
        reward_for_task(request.user, task.name, is_first_try=is_first_try)
        total_solved = Submission.objects.filter(
            user=request.user, status='accepted'
        ).count()
        _check_and_grant_achievements(request.user, total_solved, 0)

    return JsonResponse({
        'status': result['status'],
        'passed': result['passed'],
        'total': result['total'],
        'results': safe_results,
    })


@login_required
def task(request):
    try:
        student = request.user.student
        enrollment = Enrollment.objects.filter(student=student).first()
    except Exception:
        student = None
        enrollment = None

    in_group = enrollment is not None

    if in_group:
        homeworks = Homework.objects.filter(
            group=enrollment.group
        ).select_related('task', 'teacher').order_by('deadline')

        progress_map = {}
        if homeworks:
            task_ids = [hw.task_id for hw in homeworks]
            for p in UserTaskProgress.objects.filter(user=request.user, task_id__in=task_ids):
                progress_map[p.task_id] = p

        tasks_data = []
        for hw in homeworks:
            progress = progress_map.get(hw.task_id)
            tasks_data.append({
                'task': hw.task,
                'is_completed': progress.is_completed if progress else False,
                'attempts': progress.attempts if progress else 0,
                'completed_at': progress.completed_at if progress else None,
                'deadline': hw.deadline,
                'teacher': hw.teacher,
                'homework_id': hw.id,
            })

        total = len(tasks_data)
        completed = sum(1 for t in tasks_data if t['is_completed'])
        in_progress = sum(1 for t in tasks_data if t['attempts'] > 0 and not t['is_completed'])

        context = {
            'in_group': True,
            'group': enrollment.group,
            'tasks_data': tasks_data,
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
        }

    else:
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'create':
                title = request.POST.get('title', '').strip()
                description = request.POST.get('description', '').strip()
                deadline_str = request.POST.get('deadline', '').strip()
                if title:
                    from django.utils import timezone
                    import datetime
                    deadline = None
                    if deadline_str:
                        try:
                            deadline = timezone.make_aware(
                                datetime.datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                            )
                        except ValueError:
                            pass
                    pt = PersonalTask.objects.create(
                        user=request.user,
                        title=title,
                        description=description,
                        deadline=deadline
                    )
                    Notification.objects.create(
                        user=request.user,
                        text=f'📝 Новая задача добавлена: «{pt.title}»'
                    )
                return redirect('prac:task')

            elif action == 'complete':
                task_id = request.POST.get('task_id')
                PersonalTask.objects.filter(id=task_id, user=request.user).update(is_completed=True)
                return redirect('prac:task')

            elif action == 'delete':
                task_id = request.POST.get('task_id')
                PersonalTask.objects.filter(id=task_id, user=request.user).delete()
                return redirect('prac:task')

        personal_tasks = PersonalTask.objects.filter(user=request.user)
        total = personal_tasks.count()
        completed = personal_tasks.filter(is_completed=True).count()
        in_progress = personal_tasks.filter(is_completed=False).count()

        context = {
            'in_group': False,
            'personal_tasks': personal_tasks,
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
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('prac:course')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


@login_required
def edit_profile(request, username):
    user = get_object_or_404(User, username=username)

    if request.user != user:
        return redirect('prac:profile', username=username)

    form = UserEditForm(request.POST or None, instance=user)

    if form.is_valid():
        form.save()
        return redirect('prac:profile', username=username)

    return render(request, 'registration/user.html', {'form': form})


def contest_detail(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    tasks = contest.tasks.all()
    scores = ContestScore.objects.filter(contest=contest).order_by('-score')
    context = {
        'contest': contest,
        'tasks': tasks,
        'scores': scores,
    }
    return render(request, 'profile/contest_detail.html', context)


@teacher_required
def teacher_dashboard(request):
    teacher = request.user.teacher
    teacher_assignments = CourseTeacherGroup.objects.filter(teacher=teacher)
    teacher_groups = teacher_assignments.values_list('group', flat=True)
    teacher_courses = teacher_assignments.values_list('course', flat=True)

    total_students = Student.objects.filter(
        enrollment__group__id__in=teacher_groups
    ).distinct().count()
    total_courses = Course.objects.filter(id__in=teacher_courses).count()
    total_groups = Group.objects.filter(id__in=teacher_groups).count()
    total_tasks = Task.objects.filter(
        topic__course__id__in=teacher_courses
    ).distinct().count()

    recent_students = Student.objects.filter(
        enrollment__group__id__in=teacher_groups
    ).distinct().select_related('user').order_by('-id')[:5]

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
    teacher = request.user.teacher
    teacher_groups = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('group', flat=True)

    search_query = request.GET.get('search', '')
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
    teacher = request.user.teacher
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()

    courses = Course.objects.filter(
        id__in=teacher_courses_ids
    ).annotate(
        students_count=Count('students', distinct=True),
        topics_count=Count('topics', distinct=True)
    )

    context = {'courses': courses, 'teacher': teacher}
    return render(request, 'teacher/courses.html', context)


@teacher_required
def teacher_tasks(request):
    from Logistic_Task.models import Course, Topic, Task
    teacher = request.user.teacher
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()

    tasks = Task.objects.filter(
        topic__course__id__in=teacher_courses_ids
    ).distinct()

    topics = Topic.objects.filter(
        course__id__in=teacher_courses_ids
    ).annotate(tasks_count=Count('tasks')).distinct()

    context = {'tasks': tasks, 'topics': topics, 'teacher': teacher}
    return render(request, 'teacher/tasks.html', context)


@teacher_required
def teacher_student_detail(request, student_id):
    teacher = request.user.teacher
    teacher_groups = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('group', flat=True)

    student = get_object_or_404(
        Student,
        id=student_id,
        enrollment__group__id__in=teacher_groups
    )

    enrollments = Enrollment.objects.filter(
        student=student,
        group__id__in=teacher_groups
    ).select_related('group')

    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True)

    courses = student.user.enrolled_courses.filter(id__in=teacher_courses_ids)

    context = {
        'student': student,
        'enrollments': enrollments,
        'courses': courses,
        'teacher': teacher,
    }
    return render(request, 'teacher/student_detail.html', context)


@teacher_required
def teacher_assign_homework(request):
    teacher = request.user.teacher
    teacher_groups = CourseTeacherGroup.objects.filter(teacher=teacher).values_list('group', flat=True)
    teacher_courses_ids = CourseTeacherGroup.objects.filter(teacher=teacher).values_list('course', flat=True).distinct()

    groups = Group.objects.filter(id__in=teacher_groups)
    tasks = Task.objects.filter(topic__course__id__in=teacher_courses_ids).distinct()

    if request.method == 'POST':
        group_id = request.POST.get('group')
        task_id = request.POST.get('task')
        deadline_str = request.POST.get('deadline')

        try:
            from django.utils import timezone
            import datetime
            group = Group.objects.get(id=group_id)
            task = Task.objects.get(id=task_id)
            deadline = timezone.make_aware(
                datetime.datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            )
            hw, created = Homework.objects.get_or_create(
                group=group,
                task=task,
                defaults={'teacher': teacher, 'deadline': deadline}
            )
            if created:
                for student in group.students.all():
                    if student.user:
                        Notification.objects.create(
                            user=student.user,
                            text=f'📚 Новое ДЗ: «{task.name}» до {deadline.strftime("%d.%m.%Y %H:%M")}'
                        )
                messages.success(request, f'ДЗ «{task.name}» назначено группе {group.name}!')
            else:
                messages.warning(request, 'Это задание уже назначено данной группе.')
        except Exception as e:
            messages.error(request, f'Ошибка: {e}')

        return redirect('prac:teacher_assign_homework')

    homeworks = Homework.objects.filter(
        teacher=teacher
    ).select_related('group', 'task').order_by('-created_at')
    for hw in homeworks:
        students_in_group = hw.group.students.filter(user__isnull=False)
        solved_user_ids = Submission.objects.filter(
            task=hw.task,
            status='accepted',
            user__in=students_in_group.values_list('user', flat=True)
        ).values_list('user_id', flat=True).distinct()
        hw.solved_count = len(solved_user_ids)
        hw.total_count = students_in_group.count()

    context = {
        'groups': groups,
        'tasks': tasks,
        'homeworks': homeworks,
        'teacher': teacher,
    }
    return render(request, 'teacher/assign_homework.html', context)


@teacher_required
def teacher_course_create(request):
    from Logistic_Task.models import Topic
    topics = Topic.objects.all().order_by('name')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        selected_topics = request.POST.getlist('topics')
        if name:
            course = Course.objects.create(name=name)
            if selected_topics:
                course.topics.set(selected_topics)
            return redirect('prac:teacher_courses')

    return render(request, 'teacher/course_form.html', {
        'action': 'Создать', 'course': None, 'all_topics': topics, 'selected_topic_ids': []
    })


@teacher_required
def teacher_course_edit(request, course_id):
    from Logistic_Task.models import Topic
    course = get_object_or_404(Course, id=course_id)
    topics = Topic.objects.all().order_by('name')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        selected_topics = request.POST.getlist('topics')
        if name:
            course.name = name
            course.save()
            course.topics.set(selected_topics)
            return redirect('prac:teacher_courses')

    selected_topic_ids = list(course.topics.values_list('id', flat=True))
    return render(request, 'teacher/course_form.html', {
        'action': 'Сохранить', 'course': course,
        'all_topics': topics, 'selected_topic_ids': selected_topic_ids
    })


@teacher_required
def teacher_course_delete(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        course.delete()
        return redirect('prac:teacher_courses')
    return render(request, 'teacher/confirm_delete.html', {
        'object_name': course.name,
        'cancel_url': 'prac:teacher_courses',
    })


@teacher_required
def teacher_task_create(request):
    teacher = request.user.teacher
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()
    topics = Topic.objects.filter(course__id__in=teacher_courses_ids).distinct()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            task_obj = Task.objects.create(
                name=name,
                text_task=request.POST.get('text_task', '').strip() or None,
                initial_code=request.POST.get('initial_code', '').strip() or None,
                expected_output=request.POST.get('expected_output', '').strip() or None,
            )
            topic_id = request.POST.get('topic_id')
            if topic_id:
                topic = Topic.objects.get(id=topic_id)
                topic.tasks.add(task_obj)
            return redirect('prac:teacher_tasks')

    return render(request, 'teacher/task_form.html', {
        'action': 'Создать', 'task': None, 'topics': topics,
    })


@teacher_required
def teacher_task_edit(request, task_id):
    teacher = request.user.teacher
    task_obj = get_object_or_404(Task, id=task_id)
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()
    topics = Topic.objects.filter(course__id__in=teacher_courses_ids).distinct()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            task_obj.name = name
            task_obj.text_task = request.POST.get('text_task', '').strip() or None
            task_obj.initial_code = request.POST.get('initial_code', '').strip() or None
            task_obj.expected_output = request.POST.get('expected_output', '').strip() or None
            task_obj.save()
            return redirect('prac:teacher_tasks')

    return render(request, 'teacher/task_form.html', {
        'action': 'Сохранить', 'task': task_obj, 'topics': topics,
    })


@teacher_required
def teacher_task_delete(request, task_id):
    task_obj = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        task_obj.delete()
        return redirect('prac:teacher_tasks')
    return render(request, 'teacher/confirm_delete.html', {
        'object_name': task_obj.name,
        'cancel_url': 'prac:teacher_tasks',
    })


@teacher_required
def teacher_topic_create(request):
    teacher = request.user.teacher
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()
    courses = Course.objects.filter(id__in=teacher_courses_ids)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        course_id = request.POST.get('course_id')
        if name:
            topic = Topic.objects.create(name=name)
            if course_id:
                c = Course.objects.get(id=course_id)
                c.topics.add(topic)
            return redirect('prac:teacher_tasks')
    return render(request, 'teacher/topic_form.html', {
        'action': 'Создать', 'topic': None, 'courses': courses
    })


@teacher_required
def teacher_topic_edit(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    teacher = request.user.teacher
    teacher_courses_ids = CourseTeacherGroup.objects.filter(
        teacher=teacher
    ).values_list('course', flat=True).distinct()
    courses = Course.objects.filter(id__in=teacher_courses_ids)

    if request.method == 'POST':
        topic.name = request.POST.get('name', topic.name).strip()
        topic.save()
        return redirect('prac:teacher_tasks')
    return render(request, 'teacher/topic_form.html', {
        'action': 'Сохранить', 'topic': topic, 'courses': courses
    })


@teacher_required
def teacher_topic_delete(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.method == 'POST':
        topic.delete()
        return redirect('prac:teacher_tasks')
    return render(request, 'teacher/confirm_delete.html', {
        'object_name': topic.name,
        'cancel_url': 'prac:teacher_tasks',
    })


@teacher_required
def teacher_add_student(request):
    teacher = request.user.teacher
    teacher_groups = Group.objects.filter(
        id__in=CourseTeacherGroup.objects.filter(
            teacher=teacher
        ).values_list('group', flat=True)
    )

    form = AddStudentForm(
        request.POST or None,
        group_queryset=teacher_groups
    )

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data.get('email', ''),
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
        )
        student = Student.objects.create(
            user=user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data.get('phone_number') or None,
        )
        group_obj = Group.objects.get(id=data['group'])
        Enrollment.objects.create(student=student, group=group_obj)
        return redirect('prac:teacher_students')

    return render(request, 'teacher/add_student.html', {
        'form': form, 'teacher': teacher,
    })


@login_required
def leaderboard(request):
    students = Student.objects.filter(
        user__isnull=False
    ).select_related('user').prefetch_related(
        Prefetch('user__wallet')
    ).annotate(
        solved_count=Count(
            'user__submissions',
            filter=Q(user__submissions__status='accepted'),
            distinct=True
        )
    )

    def sort_key(s):
        balance = s.user.wallet.balance if hasattr(s.user, 'wallet') else 0
        return (-balance, -s.solved_count)

    students_list = sorted(students, key=sort_key)

    today = date.today()
    for i, student in enumerate(students_list):
        student.rank = i + 1
        progress = UserTaskProgress.objects.filter(
            user=student.user, is_completed=True
        ).values_list('completed_at', flat=True)
        activity = {p.strftime('%Y-%m-%d') for p in progress if p}
        streak = 0
        for d in range(365):
            day = (today - timedelta(days=d)).strftime('%Y-%m-%d')
            if day in activity:
                streak += 1
            else:
                break
        student.streak = streak
        student.balance = student.user.wallet.balance if hasattr(student.user, 'wallet') else 0

    return render(request, 'leaderboard/leaderboard.html', {
        'students': students_list,
    })
