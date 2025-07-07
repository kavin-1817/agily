from django.forms import Form, ChoiceField, Select
from django import forms
from agily.models import Project
from agily.sprints.models import Sprint


class SprintGroupByForm(Form):
    CHOICES = [
        ("", "None"),
        ("requester", "Requester"),
        ("assignee", "Assignee"),
        ("state", "State"),
        ("epic", "Epic"),
    ]

    group_by = ChoiceField(
        choices=CHOICES,
        required=False,
        widget=Select(
            attrs={
                "hx-get": ".",
                "hx-trigger": "change",
                "hx-target": "body",
                "hx-replace-url": "true",
            }
        ),
    )


class SprintForm(forms.ModelForm):
    class Meta:
        model = Sprint
        fields = ["title", "description", "starts_at", "ends_at", "project"]

    def __init__(self, *args, **kwargs):
        workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields["project"].queryset = Project.objects.filter(workspace__slug=workspace)
