from django import forms
from django.forms import Select, Form, ChoiceField, ModelChoiceField, ModelForm
from django.utils.html import format_html

from agily.users.models import User
from agily.workspaces.models import Workspace

from .models import EpicState, StoryState, Epic, Story, StoryAttachment
from agily.sprints.models import Sprint
from agily.models import Project


class SelectWithTitle(Select):
    def render(self, name, value, attrs=None, renderer=None):
        # Get the display label for the selected value, handling optgroups
        label = ""
        choices = list(getattr(self, 'choices', []))
        for option in choices:
            if isinstance(option[1], (list, tuple)):
                # Optgroup: (group_label, group_choices)
                for opt_value, opt_label in option[1]:
                    if str(opt_value) == str(value):
                        label = opt_label
                        break
            else:
                opt_value, opt_label = option
                if str(opt_value) == str(value):
                    label = opt_label
                    break
        if attrs is None:
            attrs = {}
        attrs = attrs.copy()
        if label:
            attrs["title"] = label
        return super().render(name, value, attrs, renderer)


custom_select = SelectWithTitle(
    attrs={
        "form": "object-list",
        "hx-trigger": "change",
        "hx-post": ".",
        "hx-target": "body",
    }
)


class EpicFilterForm(Form):
    state = ModelChoiceField(
        empty_label="--Set State--", queryset=EpicState.objects.all(), required=False, widget=custom_select
    )

    owner = ModelChoiceField(
        empty_label="--Set Owner--", queryset=User.objects.all(), required=False, widget=custom_select
    )


class StoryFilterForm(Form):
    state = ModelChoiceField(
        empty_label="--Set State--", queryset=StoryState.objects.all(), required=False, widget=custom_select
    )

    assignee = ModelChoiceField(
        empty_label="--Set Assignee--", queryset=User.objects.all(), required=False, widget=custom_select
    )


class EpicGroupByForm(Form):
    CHOICES = [
        ("", "None"),
        ("requester", "Requester"),
        ("assignee", "Assignee"),
        ("state", "State"),
        ("sprint", "Sprint"),
    ]

    group_by = ChoiceField(
        choices=CHOICES,
        required=False,
        widget=SelectWithTitle(
            attrs={
                "hx-trigger": "change",
                "hx-get": ".",
                "hx-target": "body",
                "hx-replace-url": "true",
            }
        ),
    )


class BaseWorkspaceModelForm(ModelForm):
    """
    Base form for models that belong to a workspace. See EpicForm and StoryForm below for usage.
    """

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        self.workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        from agily.workspaces.models import Workspace
        workspace_obj = self.workspace
        if isinstance(workspace_obj, str):
            try:
                workspace_obj = Workspace.objects.get(slug=workspace_obj)
            except Workspace.DoesNotExist:
                workspace_obj = None
        instance.workspace = workspace_obj
        if commit:
            instance.save()
        return instance


class EpicForm(BaseWorkspaceModelForm):
    priority = forms.ChoiceField(
        choices=Epic.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'input'}),
        label="Product Backlog Priority"
    )
    
    class Meta:
        model = Epic
        fields = ["project", "title", "description", "owner", "state", "priority", "tags"]
        labels = {
            "project": "Project",
            "title": "Product Backlog Title",
            "description": "Product Backlog Description",
            "owner": "Product Backlog Owner",
            "state": "Product Backlog State",
            "tags": "Product Backlog Tags",
        }
        help_texts = {
            "project": "Select the project this Product Backlog belongs to.",
            "title": "Enter the name of the Product Backlog.",
            "description": "Describe the Product Backlog.",
        }

    def __init__(self, *args, **kwargs):
        workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)
        
        # Set the workspace properly
        if workspace:
            self.workspace = workspace
        
        # Get the workspace object for filtering
        workspace_obj = self.workspace
        if isinstance(workspace_obj, str):
            try:
                workspace_obj = Workspace.objects.get(slug=workspace_obj)
            except Workspace.DoesNotExist:
                workspace_obj = None
        
        if workspace_obj:
            self.fields["owner"].queryset = User.objects.filter(is_active=True, workspace=workspace_obj).order_by("username")
            self.fields["project"].queryset = Project.objects.filter(workspace=workspace_obj).order_by("name")
        else:
            self.fields["owner"].queryset = User.objects.none()
            self.fields["project"].queryset = Project.objects.none()


class StoryForm(BaseWorkspaceModelForm):
    PRIORITY_CHOICES = [
        (2, 'High'),
        (1, 'Medium'),
        (0, 'Low'),
    ]
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, widget=forms.Select(attrs={'class': 'input'}))
    description = forms.CharField(max_length=300, widget=forms.Textarea)
    # Remove the files field entirely; handled by plain HTML input and view logic
    class Meta:
        model = Story
        fields = [
            "project",
            "title",
            "description",
            "epic",
            "sprint",
            "assignee",
            "state",
            "priority",
            "points",
        ]
        labels = {
            "epic": "Product Backlog",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)
        
        # Set the workspace properly
        if workspace:
            self.workspace = workspace
        
        # Get the workspace object for filtering
        workspace_obj = self.workspace
        if isinstance(workspace_obj, str):
            try:
                workspace_obj = Workspace.objects.get(slug=workspace_obj)
            except Workspace.DoesNotExist:
                workspace_obj = None
        
        # Set up querysets
        self.fields["assignee"].queryset = User.objects.filter(is_active=True).order_by("username")
        
        if workspace_obj:
            self.fields["epic"].queryset = Epic.objects.filter(workspace=workspace_obj).order_by("title")
            self.fields["project"].queryset = Project.objects.filter(workspace=workspace_obj).order_by("name")

            # Filter sprints by workspace and project if project is selected
            project_id = self.data.get("project") or self.initial.get("project")
            if project_id:
                self.fields["sprint"].queryset = Sprint.objects.filter(workspace=workspace_obj, project_id=project_id).order_by("ends_at")
            else:
                self.fields["sprint"].queryset = Sprint.objects.filter(workspace=workspace_obj).order_by("ends_at")
        else:
            self.fields["epic"].queryset = Epic.objects.none()
            self.fields["sprint"].queryset = Sprint.objects.none()
            self.fields["project"].queryset = Project.objects.none()
        # Optionally, set a clearer label for the sprint field
        self.fields["sprint"].label = "Sprint"

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Only set requester on creation
        if not instance.pk and self.request and self.request.user.is_authenticated:
            instance.requester = self.request.user
        if commit:
            instance.save()
        return instance


class StoryAttachmentForm(forms.ModelForm):
    class Meta:
        model = StoryAttachment
        fields = ["file", "description"]
