from django import forms

from directories.models import Employee, WorkObject, WorkType

from .models import Document


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Ivanov worklog 2026-07-06",
                }
            ),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class WorklogReviewForm(forms.Form):
    employee_name = forms.ChoiceField(label="Employee", widget=forms.Select(attrs={"class": "form-select"}))
    date = forms.DateField(
        label="Date",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    object = forms.ChoiceField(label="Work object", widget=forms.Select(attrs={"class": "form-select"}))
    work_type = forms.ChoiceField(label="Work type", widget=forms.Select(attrs={"class": "form-select"}))
    hours = forms.DecimalField(
        label="Hours",
        min_value=0.01,
        max_value=24,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.25", "min": "0.01", "max": "24"}),
    )
    comment = forms.CharField(
        label="Comment",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, document: Document | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        current = (document.normalized_json or {}) if document else {}
        self.fields["employee_name"].choices = self._name_choices(Employee, "full_name", current.get("employee_name"))
        self.fields["object"].choices = self._name_choices(WorkObject, "name", current.get("object"))
        self.fields["work_type"].choices = self._name_choices(WorkType, "name", current.get("work_type"))

        if document and not self.is_bound:
            self.initial.update(
                {
                    "employee_name": current.get("employee_name"),
                    "date": current.get("date"),
                    "object": current.get("object"),
                    "work_type": current.get("work_type"),
                    "hours": current.get("hours"),
                    "comment": current.get("comment"),
                }
            )

    def to_review_data(self) -> dict:
        return {
            "employee_name": self.cleaned_data["employee_name"],
            "date": self.cleaned_data["date"].isoformat(),
            "object": self.cleaned_data["object"],
            "work_type": self.cleaned_data["work_type"],
            "hours": str(self.cleaned_data["hours"]),
            "comment": self.cleaned_data.get("comment") or None,
        }

    def _name_choices(self, model, field_name: str, current_value: str | None):
        values = list(model.objects.active().values_list(field_name, flat=True))
        if current_value and current_value not in values:
            values.insert(0, current_value)
        return [(value, value) for value in values]
