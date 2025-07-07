from django import forms
from .models import Issue, IssueAttachment
from agily.models import Project
from django.forms import modelformset_factory


class SearchForm(forms.Form):
    q = forms.CharField(
        help_text="Click to see help & options",
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "on",
                "placeholder": "Search for...",
            }
        ),
    )


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["title", "description", "status", "assignee"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request and self.request.user.is_authenticated:
            instance.requester = self.request.user
        if commit:
            instance.save()
        return instance


class IssueGlobalForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["project", "title", "description", "status", "assignee"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request and self.request.user.is_authenticated:
            instance.requester = self.request.user
        if commit:
            instance.save()
        return instance


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request:
            workspace_slug = self.request.session.get("current_workspace")
            if workspace_slug:
                from agily.workspaces.models import Workspace
                try:
                    workspace = Workspace.objects.get(slug=workspace_slug)
                    instance.workspace = workspace
                except Workspace.DoesNotExist:
                    raise forms.ValidationError(f"Workspace '{workspace_slug}' not found")
            else:
                raise forms.ValidationError("No workspace selected")
        if commit:
            instance.save()
        return instance


class MultiIssueAttachmentForm(forms.Form):
    description = forms.CharField(max_length=255, required=False)


class IssueAttachmentForm(forms.ModelForm):
    class Meta:
        model = IssueAttachment
        fields = ["file", "description"]


IssueAttachmentFormSet = modelformset_factory(
    IssueAttachment,
    form=IssueAttachmentForm,
    extra=3,  # Number of empty forms shown by default
    can_delete=False,
)
