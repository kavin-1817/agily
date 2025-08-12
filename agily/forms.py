from django import forms
from django.db.models import Q
from .models import Issue, IssueAttachment, Project, Notification
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


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['message', 'link']
        widgets = {
            'message': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter notification message'}),
            'link': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Optional: Enter a URL for this notification'}),
        }
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)


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
                    
                    # Filter assignee dropdown to exclude testers and superusers
                    if "assignee" in self.fields:
                        from django.contrib.auth import get_user_model
                        from django.contrib.auth.models import Group
                        User = get_user_model()
                        
                        # Get all users who are testers or superusers
                        tester_groups = Group.objects.filter(name__in=["tester", "testers"])
                        tester_users = User.objects.filter(groups__in=tester_groups)
                        superusers = User.objects.filter(is_superuser=True)
                        
                        # Exclude these users from the assignee dropdown
                        excluded_users = tester_users.union(superusers)
                        self.fields["assignee"].queryset = User.objects.exclude(
                            id__in=excluded_users.values_list("id", flat=True)
                        ).filter(is_active=True)
                        
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
        # Initialize project variable
        project = None
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
                    
                    # Filter assignee dropdown to exclude testers and superusers
                    if "assignee" in self.fields:
                        from django.contrib.auth import get_user_model
                        from django.contrib.auth.models import Group
                        User = get_user_model()
                        
                        # Get all users who are testers or superusers
                        tester_groups = Group.objects.filter(name__in=["tester", "testers"])
                        tester_users = User.objects.filter(groups__in=tester_groups)
                        superusers = User.objects.filter(is_superuser=True)
                        
                        # Exclude these users from the assignee dropdown
                        excluded_users = tester_users.union(superusers)
                        self.fields["assignee"].queryset = User.objects.exclude(
                            id__in=excluded_users.values_list("id", flat=True)
                        ).filter(is_active=True)
                        
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
        # Initialize project variable
        project = None
        # Only require project if the field is present in the form
        if "project" in self.fields:
            project = cleaned_data.get("project")
            if not project:
                raise forms.ValidationError("You must select a project.")
        # Duplicate check: title + project (optionally add description for stricter check)
        title = cleaned_data.get("title")
        description = cleaned_data.get("description", "")
        if project and title:
            qs = Issue.objects.filter(project=project, title=title)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("An issue with this title already exists in the selected project.")
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
        
        # Only show active users who are super admins or in project admin group
        from django.contrib.auth.models import Group
        project_admin_group = Group.objects.filter(name__in=["project admin", "project admins"]).first()
        self.fields["project_admin"].queryset = User.objects.filter(
            Q(is_superuser=True) | 
            Q(groups=project_admin_group),
            is_active=True
        )
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
