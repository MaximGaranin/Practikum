from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class AddStudentForm(forms.Form):
    username = forms.CharField(
        label='Username', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        label='Имя', max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label='Фамилия', max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label='Email', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label='Телефон', required=False, max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7...'})
    )
    group = forms.ChoiceField(
        label='Группа',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, group_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group_queryset is not None:
            self.fields['group'].choices = [
                (g.id, g.name) for g in group_queryset
            ]
        else:
            self.fields['group'].choices = []

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким username уже существует.')
        return username

