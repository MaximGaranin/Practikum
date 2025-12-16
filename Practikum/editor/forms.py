from django import forms
from .models import CodeSnippet

class CodeEditorForm(forms.ModelForm):
    class Meta:
        model = CodeSnippet
        fields = ['title', 'code', 'language']
        widgets = {
            'code': forms.Textarea(attrs={
                'id': 'code-editor',
                'rows': 20,
                'cols': 80
            })
        }
