from django.contrib import admin
from django import forms
from .models import Student, Group, Enrollment


class EnrollmentInlineForStudent(admin.StackedInline):
    model = Enrollment
    autocomplete_fields = ['group']


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'placeholder': '+7 999 123-45-67',
                'pattern': r'\+?[0-9\s\-\(\)]+',
            })
        }


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['id', 'last_name', 'first_name', 'user']
    search_fields = ['first_name', 'last_name', 'user__username', 'user__email']
    inlines = [EnrollmentInlineForStudent]
    autocomplete_fields = ['user']

class EnrollmentInline(admin.StackedInline):
    model = Enrollment
    autocomplete_fields = ['student']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    inlines = [EnrollmentInline]
    search_fields = ['name']
