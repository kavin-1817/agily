from django import forms
from .models import Issue, IssueAttachment, Project
from django.conf import settings
from django.contrib.auth import get_user_model
from agily.workspaces.models import Workspace  # Ensure Workspace is imported for type checking
from django.forms import modelformset_factory

User = get_user_model()


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
        fields = ["project", "title", "description", "status", "severity", "assignee", "solution"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Restrict fields for developers editing issues assigned to them
        if self.request and self.instance and self.instance.pk:
            group_names = [g.name.lower().strip() for g in self.request.user.groups.all()]
            is_developer = any(g in ["developer", "developers"] for g in group_names)
            if is_developer and self.instance.assignee == self.request.user:
                allowed = ["status", "solution"]
                for field in list(self.fields.keys()):
                    if field not in allowed:
                        self.fields.pop(field)
        # Filter projects based on current workspace
        if self.request:
            workspace_slug = self.request.session.get("current_workspace")
            if workspace_slug:
                try:
                    workspace = Workspace.objects.get(slug=workspace_slug)
                    projects = Project.objects.filter(workspace=workspace).order_by("name")
                    if "project" in self.fields:
                        self.fields["project"].queryset = projects
                        if not projects.exists():
                            self.fields["project"].help_text = "No projects available in this workspace. Please create a project first."
                            self.fields["project"].widget.attrs["disabled"] = "disabled"
                except Workspace.DoesNotExist:
                    if "project" in self.fields:
                        self.fields["project"].queryset = Project.objects.none()
                        self.fields["project"].help_text = "Workspace not found."
            else:
                if "project" in self.fields:
                    self.fields["project"].queryset = Project.objects.none()
                    self.fields["project"].help_text = "No workspace selected."

    def clean(self):
        cleaned_data = super().clean()
        # Only require project if the field is present in the form
        if "project" in self.fields:
            project = cleaned_data.get("project")
            if not project:
                raise forms.ValidationError("Please select a project for this issue.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Only set requester if creating a new issue
        if self.request and self.request.user.is_authenticated and instance.pk is None:
            instance.requester = self.request.user
        if commit:
            instance.save()
        return instance


class IssueGlobalForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["project", "title", "description", "status", "severity", "assignee", "solution"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Restrict fields for developers editing issues assigned to them
        if self.request and self.instance and self.instance.pk:
            group_names = [g.name.lower().strip() for g in self.request.user.groups.all()]
            is_developer = any(g in ["developer", "developers"] for g in group_names)
            if is_developer and self.instance.assignee == self.request.user:
                allowed = ["status", "solution"]
                for field in list(self.fields.keys()):
                    if field not in allowed:
                        self.fields.pop(field)
        # Filter projects based on current workspace
        if self.request:
            workspace_slug = self.request.session.get("current_workspace")
            if workspace_slug:
                try:
                    workspace = Workspace.objects.get(slug=workspace_slug)
                    projects = Project.objects.filter(workspace=workspace).order_by("name")
                    if "project" in self.fields:
                        self.fields["project"].queryset = projects
                        if not projects.exists():
                            self.fields["project"].help_text = "No projects available in this workspace. Please create a project first."
                            self.fields["project"].widget.attrs["disabled"] = "disabled"
                except Workspace.DoesNotExist:
                    if "project" in self.fields:
                        self.fields["project"].queryset = Project.objects.none()
                        self.fields["project"].help_text = "Workspace not found."
            else:
                if "project" in self.fields:
                    self.fields["project"].queryset = Project.objects.none()
                    self.fields["project"].help_text = "No workspace selected."

    def clean(self):
        cleaned_data = super().clean()
        # Only require project if the field is present in the form
        if "project" in self.fields:
            project = cleaned_data.get("project")
            if not project:
                raise forms.ValidationError("Please select a project for this issue.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Only set requester if creating a new issue
        if self.request and self.request.user.is_authenticated and instance.pk is None:
            instance.requester = self.request.user
        if commit:
            instance.save()
        return instance


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "project_admin"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        
        # Only show active users as potential project admins
        self.fields["project_admin"].queryset = User.objects.filter(is_active=True)
        self.fields["project_admin"].label = "Project Admin"
        self.fields["project_admin"].help_text = "Select the user who will be the admin for this project"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request:
            workspace_slug = self.request.session.get("current_workspace")
            if workspace_slug:
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
