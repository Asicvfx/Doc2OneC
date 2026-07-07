from django import forms

from .models import Document


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: Отчет Иванов 2026-07-06",
                }
            ),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
