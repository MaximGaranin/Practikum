from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import models, transaction
from Logistic_Task.models import Course, Topic, Task
from .models import (
    Student, Group, Enrollment, Teacher, CourseTeacherGroup
)


# ============= INLINE КЛАССЫ =============

class EnrollmentInline(admin.TabularInline):
    """Inline для отображения записей студентов в группы."""
    model = Enrollment
    extra = 1
    raw_id_fields = ['student']
    readonly_fields = ['date']
    verbose_name = 'Студент в группе'
    verbose_name_plural = 'Студенты в группе'


class CourseTeacherGroupInline(admin.TabularInline):
    """Inline для назначения преподавателей на курсы и группы."""
    model = CourseTeacherGroup
    extra = 1
    fields = ['course', 'group', 'start_date']
    readonly_fields = ['start_date']
    verbose_name = 'Назначение на курс и группу'
    verbose_name_plural = 'Назначения на курсы и группы'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показываем только активные курсы и группы."""
        if db_field.name == "course":
            kwargs["queryset"] = Course.objects.all().order_by('name')
        if db_field.name == "group":
            kwargs["queryset"] = Group.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TaskInline(admin.TabularInline):
    """Inline для заданий в теме."""
    model = Topic.tasks.through
    extra = 1
    verbose_name = 'Задание'
    verbose_name_plural = 'Задания темы'


class TopicInline(admin.TabularInline):
    """Inline для тем в курсе."""
    model = Course.topics.through
    extra = 1
    verbose_name = 'Тема'
    verbose_name_plural = 'Темы курса'


# ============= ADMIN КЛАССЫ =============

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Админка студентов."""
    list_display = ['id', 'last_name', 'first_name', 'user', 'phone_number', 'get_groups']
    list_display_links = ['id', 'last_name', 'first_name']
    search_fields = ['first_name', 'last_name', 'user__username', 'user__email', 'phone_number']
    list_filter = ['enrollment__group']
    raw_id_fields = ['user']
    inlines = [EnrollmentInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'first_name', 'last_name')
        }),
        ('Контакты', {
            'fields': ('phone_number',)
        }),
    )
    
    def get_groups(self, obj):
        """Показывает группы студента."""
        groups = obj.group_set.all()
        return ', '.join([g.name for g in groups]) if groups else '-'
    get_groups.short_description = 'Группы'


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Админка групп."""
    list_display = ['id', 'name', 'get_students_count']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    inlines = [EnrollmentInline]
    
    def get_students_count(self, obj):
        """Количество студентов в группе."""
        return obj.students.count()
    get_students_count.short_description = 'Количество студентов'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Админка зачисления студентов в группы."""
    list_display = ['id', 'student', 'group', 'date']
    list_display_links = ['id']
    list_filter = ['group', 'date']
    search_fields = ['student__first_name', 'student__last_name', 'group__name']
    raw_id_fields = ['student', 'group']
    date_hierarchy = 'date'
    readonly_fields = ['date']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    """Админка преподавателей с автоматическим созданием пользователя."""
    list_display = ['id', 'last_name', 'first_name', 'user', 'phone_number', 'get_courses_count', 'get_groups_count']
    search_fields = ['first_name', 'last_name', 'user__username', 'user__email']
    inlines = [CourseTeacherGroupInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('first_name', 'last_name')
        }),
        ('Контакты', {
            'fields': ('phone_number',)
        }),
    )
    
    readonly_fields = []
    
    def get_fieldsets(self, request, obj=None):
        """Показываем дополнительные поля только при создании."""
        if obj:  # Редактирование существующего преподавателя
            return (
                ('Основная информация', {
                    'fields': ('user', 'first_name', 'last_name')
                }),
                ('Контакты', {
                    'fields': ('phone_number',)
                }),
            )
        else:  # Создание нового преподавателя
            return (
                 ('Или выберите существующего', {
                    'fields': ('user',),
                }),
                ('Основная информация', {
                    'fields': ('first_name', 'last_name')
                }),
                ('Контакты', {
                    'fields': ('phone_number',)
                }),
            )
    
    def get_form(self, request, obj=None, **kwargs):
        """Добавляем поля для создания пользователя."""
        form = super().get_form(request, obj, **kwargs)
        
        if not obj:  # Только при создании
            from django import forms
            
            # Добавляем поля для создания пользователя
            form.base_fields['username'] = forms.CharField(
                max_length=150,
                required=False,
                help_text='Имя пользователя для входа в систему',
                label='Username'
            )
            form.base_fields['email'] = forms.EmailField(
                required=False,
                help_text='Email преподавателя',
                label='Email'
            )
            form.base_fields['password'] = forms.CharField(
                widget=forms.PasswordInput,
                required=False,
                help_text='Пароль (минимум 8 символов)',
                label='Пароль'
            )
        
        return form
    
    @transaction.atomic
    def save_model(self, request, obj, form, change):
        """Автоматически создаем пользователя при создании преподавателя."""
        if not change and not obj.user:  # Только при создании и если пользователь не указан
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            if username and password:
                # Создаем нового пользователя
                user = User.objects.create(
                    username=username,
                    email=email or '',
                    first_name=obj.first_name,
                    last_name=obj.last_name,
                    password=make_password(password),
                    is_staff=True  # Даем доступ к админке
                )
                obj.user = user
                
                self.message_user(
                    request,
                    f'Пользователь "{username}" успешно создан. Пароль установлен.',
                    level='SUCCESS'
                )
        
        super().save_model(request, obj, form, change)
    
    def get_courses_count(self, obj):
        """Количество курсов преподавателя."""
        return CourseTeacherGroup.objects.filter(teacher=obj).values('course').distinct().count()
    get_courses_count.short_description = 'Курсов'
    
    def get_groups_count(self, obj):
        """Количество групп преподавателя."""
        return CourseTeacherGroup.objects.filter(teacher=obj).values('group').distinct().count()
    get_groups_count.short_description = 'Групп'


@admin.register(CourseTeacherGroup)
class CourseTeacherGroupAdmin(admin.ModelAdmin):
    """Админка назначений преподавателей на курсы и группы."""
    list_display = ['id', 'teacher', 'course', 'group', 'start_date', 'get_students_count']
    list_display_links = ['id']
    list_filter = ['teacher', 'course', 'group', 'start_date']
    search_fields = [
        'teacher__first_name', 'teacher__last_name',
        'course__name', 'group__name'
    ]
    raw_id_fields = ['teacher']
    date_hierarchy = 'start_date'
    readonly_fields = ['start_date']
    
    fieldsets = (
        ('Назначение', {
            'fields': ('teacher', 'course', 'group')
        }),
        ('Информация', {
            'fields': ('start_date',)
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Сортировка для выпадающих списков."""
        if db_field.name == "course":
            kwargs["queryset"] = Course.objects.all().order_by('name')
        if db_field.name == "group":
            kwargs["queryset"] = Group.objects.all().order_by('name')
        if db_field.name == "teacher":
            kwargs["queryset"] = Teacher.objects.all().order_by('last_name', 'first_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_students_count(self, obj):
        """Количество студентов в группе."""
        return obj.group.students.count()
    get_students_count.short_description = 'Студентов'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Админка курсов."""
    list_display = ['id', 'name', 'get_topics_count', 'get_students_count', 'get_teachers_count']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    filter_horizontal = ['topics', 'students']
    inlines = [TopicInline]
    
    def get_topics_count(self, obj):
        """Количество тем в курсе."""
        return obj.topics.count()
    get_topics_count.short_description = 'Тем'
    
    def get_students_count(self, obj):
        """Количество студентов на курсе."""
        return obj.students.count()
    get_students_count.short_description = 'Студентов'
    
    def get_teachers_count(self, obj):
        """Количество преподавателей курса."""
        return CourseTeacherGroup.objects.filter(course=obj).values('teacher').distinct().count()
    get_teachers_count.short_description = 'Преподавателей'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Админка тем."""
    list_display = ['id', 'name', 'image', 'get_tasks_count']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    filter_horizontal = ['tasks']
    inlines = [TaskInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'image')
        }),
        ('Задания', {
            'fields': ('tasks',)
        }),
    )
    
    def get_tasks_count(self, obj):
        """Количество заданий в теме."""
        return obj.tasks.count()
    get_tasks_count.short_description = 'Заданий'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Админка заданий."""
    list_display = ['id', 'name', 'get_short_text']
    list_display_links = ['id', 'name']
    search_fields = ['name', 'text_task']
    
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        ('Содержание', {
            'fields': ('text_task',),
            'classes': ('wide',)
        }),
    )
    
    def get_short_text(self, obj):
        """Короткое описание задания."""
        if obj.text_task:
            import re
            text = re.sub('<[^<]+?>', '', obj.text_task)
            return text[:50] + '...' if len(text) > 50 else text
        return '-'
    get_short_text.short_description = 'Описание'


# ============= РАСШИРЕНИЕ USER ADMIN =============

class StudentInline(admin.StackedInline):
    """Inline студента в User."""
    model = Student
    can_delete = False
    verbose_name = 'Профиль студента'
    verbose_name_plural = 'Профиль студента'
    fk_name = 'user'


class TeacherInline(admin.StackedInline):
    """Inline преподавателя в User."""
    model = Teacher
    can_delete = False
    verbose_name = 'Профиль преподавателя'
    verbose_name_plural = 'Профиль преподавателя'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    """Расширенная админка пользователей."""
    inlines = (StudentInline, TeacherInline)


# Перерегистрируем User с новыми inline
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

