from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, Case, When, Count, Max, Value, BooleanField
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseRedirect, FileResponse, Http404
from django.urls import reverse_lazy, reverse
from django.utils.encoding import smart_str
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.views.generic.edit import DeleteView, FormView
from django.shortcuts import get_object_or_404, render, redirect
from django import forms
import json
import os
import uuid
from datetime import datetime
from .models import Project, Issue, IssueAttachment
from .forms import IssueForm, IssueGlobalForm, ProjectForm, IssueAttachmentForm, IssueAttachmentFormSet, MultiIssueAttachmentForm
from agily.workspaces.models import Workspace
from agily.users.forms import UserRegistrationForm
import pandas as pd

class BaseListView(ListView):
    paginate_by = 6
    filter_fields = {}
    select_related = None
    prefetch_related = None

    def _build_filters(self, q):
        params = {}
        for part in (q or "").split():
            if ":" in part:
                field, value = part.split(":")
                try:
                    operator = self.filter_fields[field]
                    params[operator] = value
                except KeyError:
                    continue
            else:
                params["title__icontains"] = part
        return params

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get("q") is not None:
            context["show_all_url"] = self.request.path
        context["title"] = self.model._meta.verbose_name_plural.capitalize()
        context["singular_title"] = self.model._meta.verbose_name.capitalize()
        if "workspace" in self.kwargs:
            context["current_workspace"] = self.kwargs["workspace"]
        return context

    def get_queryset(self):
        qs = self.model.objects
        q = self.request.GET.get("q")
        params = {}

        # Fix: Use project__workspace__slug for Issue model
        if "workspace" in self.kwargs:
            if hasattr(self.model, 'project'):
                params = dict(project__workspace__slug=self.kwargs["workspace"])
            else:
                params = dict(workspace__slug=self.kwargs["workspace"])

        if q is None:
            qs = qs.filter(**params) if params else qs.all()
        else:
            params.update(self._build_filters(q))
            qs = qs.filter(**params)

        if self.select_related is not None:
            qs = qs.select_related(*self.select_related)

        if self.prefetch_related is not None:
            qs = qs.prefetch_related(*self.prefetch_related)

        return qs

@method_decorator(login_required, name="dispatch")
class ProjectListView(BaseListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        qs = super().get_queryset()
        workspace_slug = self.request.session.get("current_workspace")
        if workspace_slug:
            qs = qs.filter(workspace__slug=workspace_slug)
        return qs

    def post(self, request, *args, **kwargs):
        # Bulk delete logic
        if request.POST.get("remove") == "yes":
            # Only superusers or project admins can delete
            group_names = [g.name.lower().strip() for g in request.user.groups.all()]
            is_superuser = request.user.is_superuser
            is_project_admin = "project admin" in group_names

            if not (is_superuser or is_project_admin):
                return HttpResponseForbidden(b"You do not have permission to delete projects.")

            # Collect selected project IDs
            project_ids = [key.split("project-")[1] for key in request.POST.keys() if key.startswith("project-")]

            if project_ids:
                from agily.tasks import remove_projects
                remove_projects.delay(project_ids)
                return redirect("project-list")

        return self.get(request, *args, **kwargs)

@method_decorator([login_required, user_passes_test(lambda u: u.is_staff)], name="dispatch")
class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden(b"Only superusers can create projects.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_success_url(self):
        return "/projects/"

@method_decorator(login_required, name="dispatch")
class ProjectDetailView(DetailView):
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def post(self, request, *args, **kwargs):
        if request.POST.get("remove") == "yes":
            obj = self.get_object()
            # Allow only superusers or the project admin to delete
            if request.user.is_superuser or request.user == obj.project_admin:
                obj.delete()
                return redirect("project-list")
            else:
                return HttpResponseForbidden(b"You do not have permission to delete this project.")
        return self.get(request, *args, **kwargs)

@method_decorator(login_required, name="dispatch")
class ProjectUpdateView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden(b"Only superusers can edit projects.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_success_url(self):
        return reverse_lazy("project-detail", kwargs={"pk": self.object.pk})

@method_decorator(login_required, name="dispatch")
class ProjectDeleteView(DeleteView):
    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("project-list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden(b"Only superusers can delete projects.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # If the request is from the list page, delete immediately
        if request.POST.get("remove") == "yes":
            self.object = self.get_object()
            self.object.delete()
            return redirect("project-list")
        # Otherwise, fall back to default (confirmation page)
        return super().post(request, *args, **kwargs)

@method_decorator(login_required, name="dispatch")
class IssueGlobalListView(BaseListView):
    model = Issue
    template_name = "projects/issue_list.html"
    filter_fields = {}
    select_related = None
    prefetch_related = None

    def get_queryset(self):
        qs = super().get_queryset()

        # Filter by workspace if present
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            qs = qs.filter(project__workspace__slug=workspace_slug)

        project_id = self.request.GET.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)

        assignee_id = self.request.GET.get("assignee")
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)

        issue_id = self.request.GET.get("id")
        if issue_id:
            qs = qs.filter(id=issue_id)

        severity_order = Case(
            When(severity="stopper", then=0),
            When(severity="critical", then=1),
            When(severity="high", then=2),
            When(severity="medium", then=3),
            When(severity="low", then=4),
            default=4,
            output_field=models.IntegerField(),
        )

        return qs.order_by(severity_order, "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_slug = self.kwargs.get("workspace")

        if workspace_slug:
            projects = Project.objects.filter(workspace__slug=workspace_slug).order_by("name")
            context["projects"] = projects
            context["current_workspace"] = workspace_slug
        else:
            context["projects"] = Project.objects.all()

        context["project"] = None
        context["global_issues"] = not bool(self.kwargs.get("workspace"))

        # Add assignees for filter dropdown
        from django.contrib.auth import get_user_model
        User = get_user_model()
        assignees = User.objects.filter(is_active=True, assigned_issues__isnull=False).distinct().order_by("username")
        context["assignees"] = assignees
        context["selected_assignee_id"] = self.request.GET.get("assignee", "")

        return context

@method_decorator(login_required, name="dispatch")
class IssueGlobalCreateView(CreateView):
    form_class = IssueGlobalForm
    template_name = "projects/issue_form.html"

    def dispatch(self, request, *args, **kwargs):
        group_names = [g.name.lower().strip() for g in request.user.groups.all()]
        # Allow only superusers, project admins, or testers to create issues
        if (request.user.is_superuser or
            "project admin" in group_names or
            "tester" in group_names or
            "testers" in group_names):
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseForbidden(b"You do not have permission to create issues.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_slug = self.kwargs.get("workspace") or self.request.session.get("current_workspace")

        if workspace_slug:
            projects = Project.objects.filter(workspace__slug=workspace_slug).order_by("name")
            context["available_projects"] = projects
            context["no_projects"] = not projects.exists()
            context["current_workspace"] = workspace_slug
        else:
            context["available_projects"] = []
            context["no_projects"] = True

        if self.request.POST or self.request.FILES:
            context["attachment_form"] = MultiIssueAttachmentForm(self.request.POST, self.request.FILES)
        else:
            context["attachment_form"] = MultiIssueAttachmentForm()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        attachment_form = context["attachment_form"]
        response = super().form_valid(form)

        if attachment_form.is_valid():
            files = self.request.FILES.getlist("files")
            description = attachment_form.cleaned_data.get("description", "")
            for f in files:
                IssueAttachment.objects.create(issue=self.object, file=f, description=description, uploaded_by=self.request.user)

        return response

    def get_success_url(self):
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            return reverse_lazy("workspace-issue-list", kwargs={"workspace": workspace_slug})
        return reverse_lazy("global-issue-list")

@method_decorator(login_required, name="dispatch")
class IssueGlobalUpdateView(UpdateView):
    model = Issue
    form_class = IssueGlobalForm
    template_name = "projects/issue_form.html"

    def dispatch(self, request, *args, **kwargs):
        group_names = [g.name.lower().strip() for g in request.user.groups.all()]
        # Allow only superusers, project admins, testers, or developers to edit issues
        if (request.user.is_superuser or
            "project admin" in group_names or
            "tester" in group_names or
            "testers" in group_names):
            return super().dispatch(request, *args, **kwargs)

        if ("developer" in group_names or "developers" in group_names):
            issue = self.get_object()
            if issue.assignee_id == request.user.id:
                return super().dispatch(request, *args, **kwargs)
            return HttpResponseForbidden(b"You can only edit issues assigned to you.")

        return HttpResponseForbidden(b"You do not have permission to edit issues.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_slug = self.kwargs.get("workspace") or self.request.session.get("current_workspace")

        if workspace_slug:
            projects = Project.objects.filter(workspace__slug=workspace_slug).order_by("name")
            context["available_projects"] = projects
            context["no_projects"] = not projects.exists()
            context["current_workspace"] = workspace_slug
        else:
            context["available_projects"] = []
            context["no_projects"] = True

        if self.request.POST or self.request.FILES:
            context["attachment_form"] = MultiIssueAttachmentForm(self.request.POST, self.request.FILES)
        else:
            context["attachment_form"] = MultiIssueAttachmentForm()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        attachment_form = context["attachment_form"]
        response = super().form_valid(form)

        if attachment_form.is_valid():
            files = self.request.FILES.getlist("files")
            description = attachment_form.cleaned_data.get("description", "")
            for f in files:
                IssueAttachment.objects.create(issue=self.object, file=f, description=description, uploaded_by=self.request.user)

        return response

    def get_success_url(self):
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            return reverse_lazy("workspace-issue-list", kwargs={"workspace": workspace_slug})
        return reverse_lazy("global-issue-list")

@method_decorator(login_required, name="dispatch")
class IssueGlobalDetailView(DetailView):
    model = Issue
    template_name = "projects/issue_detail.html"
    context_object_name = "issue"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            context["current_workspace"] = workspace_slug

        # Split attachments by developer/non-developer
        issue = self.object
        developer_attachments = []
        other_attachments = []

        for att in issue.attachments.all():
            if att.uploaded_by and att.uploaded_by.groups.filter(name__in=["developer", "developers"]).exists():
                developer_attachments.append(att)
            else:
                other_attachments.append(att)

        context["developer_attachments"] = developer_attachments
        context["other_attachments"] = other_attachments

        return context

@method_decorator(login_required, name="dispatch")
class IssueGlobalDeleteView(DeleteView):
    model = Issue
    template_name = "projects/issue_confirm_delete.html"
    success_url = reverse_lazy("global-issue-list")

    def dispatch(self, request, *args, **kwargs):
        group_names = [g.name.lower().strip() for g in request.user.groups.all()]
        # Allow only superusers, project admins, or testers to delete issues
        if (request.user.is_superuser or
            "project admin" in group_names or
            "tester" in group_names or
            "testers" in group_names):
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseForbidden(b"You do not have permission to delete issues.")

    def get_success_url(self):
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            return reverse_lazy("workspace-issue-list", kwargs={"workspace": workspace_slug})
        return reverse_lazy("global-issue-list")

@login_required
def upload_issue_attachment(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    if request.method == "POST":
        form = IssueAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.issue = issue
            attachment.save()
            messages.success(request, "Attachment uploaded successfully.")
            return redirect("issue-detail", pk=issue.pk)
    else:
        form = IssueAttachmentForm()

    return render(request, "projects/issue_attachment_form.html", {"form": form, "issue": issue})

@login_required
def download_issue_attachment(request, pk):
    attachment = get_object_or_404(IssueAttachment, pk=pk)

    file_handle = attachment.file.open('rb')
    filename = os.path.basename(attachment.file.name)
    response = FileResponse(file_handle, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{smart_str(filename)}"'
    response['Content-Length'] = attachment.file.size
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

@login_required
def delete_issue_attachment(request, pk):
    attachment = get_object_or_404(IssueAttachment, pk=pk)
    issue = attachment.issue

    # Check user permissions
    group_names = [g.name.lower().strip() for g in request.user.groups.all()]
    is_project_admin = "project admin" in group_names
    is_tester = any(g in ["tester", "testers"] for g in group_names)

    # Only allow superusers, project admins, or testers to delete attachments
    if not (request.user.is_superuser or is_project_admin or is_tester):
        return HttpResponseForbidden("You do not have permission to delete attachments.")

    # Check if this is a fresh request or a resubmission
    attachment_token = f"delete_issue_attachment_{pk}"

    if request.method == "POST":
        # Only process if we haven't seen this token before
        if attachment_token not in request.session or not request.session[attachment_token]:
            # Mark that we've seen this token
            request.session[attachment_token] = True
            request.session.modified = True

            # Delete the attachment
            attachment.delete()
            messages.success(request, "Attachment deleted successfully.")
        else:
            # This is a duplicate submission, just redirect with no action
            messages.info(request, "This attachment was already deleted.")

        return redirect("global-issue-detail", pk=issue.pk)

    # GET request - create a fresh token for this view
    request.session[attachment_token] = False
    request.session.modified = True

    return render(request, "projects/issue_attachment_confirm_delete.html", {"attachment": attachment})

def public_test_view(request):
    form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

class IssueExportView(View):
    def get(self, request, *args, **kwargs):
        # Get the queryset based on filters
        workspace_slug = kwargs.get("workspace")
        queryset = Issue.objects.all()
        
        if workspace_slug:
            queryset = queryset.filter(project__workspace__slug=workspace_slug)

        # Apply filters from request.GET
        project_id = request.GET.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        assignee_id = request.GET.get("assignee")
        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)

        # ADD ORDER BY ID HERE - This ensures consistent ordering
        queryset = queryset.order_by('id')

        # Convert queryset to DataFrame - REMOVED 'solution' field as per previous requirements
        issue_data = list(queryset.values(
            'id', 'title', 'description', 'status', 'severity',
            'project__name', 'requester__username', 'assignee__username',
            'created_at', 'updated_at'  # Removed 'solution'
        ))

        # Rename columns for better readability
        df = pd.DataFrame(issue_data)
        if not df.empty:
            # Convert timezone-aware datetimes to timezone-naive
            if 'created_at' in df.columns:
                df['created_at'] = df['created_at'].dt.tz_localize(None)
            if 'updated_at' in df.columns:
                df['updated_at'] = df['updated_at'].dt.tz_localize(None)
            
            df = df.rename(columns={
                'project__name': 'project',
                'requester__username': 'requester',
                'assignee__username': 'assignee'
            })

        # Create response with Excel file
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=issues.xlsx'

        # Write DataFrame to Excel
        if not df.empty:
            df.to_excel(response, index=False, engine='openpyxl')
        else:
            # Create empty DataFrame with columns - REMOVED 'solution' field
            empty_df = pd.DataFrame(columns=[
                'id', 'title', 'description', 'status', 'severity',
                'project', 'requester', 'assignee',
                'created_at', 'updated_at'  # Removed 'solution'
            ])
            empty_df.to_excel(response, index=False, engine='openpyxl')

        return response


class IssueImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel File",
        help_text="Upload an Excel file (.xlsx) containing issue data"
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=True,
        help_text="Select the project for the imported issues"
    )

    def __init__(self, *args, **kwargs):
        workspace = kwargs.pop('workspace', None)
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['project'].queryset = Project.objects.filter(workspace=workspace)

class IssueImportView(FormView):
    template_name = "projects/issue_import.html"
    form_class = IssueImportForm

    def get_success_url(self):
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            return reverse_lazy("workspace-issue-list", kwargs={"workspace": workspace_slug})
        return reverse_lazy("global-issue-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        workspace_slug = self.kwargs.get("workspace")
        if workspace_slug:
            try:
                workspace = Workspace.objects.get(slug=workspace_slug)
                kwargs['workspace'] = workspace
            except Workspace.DoesNotExist:
                pass
        return kwargs

    def form_valid(self, form):
        excel_file = form.cleaned_data['excel_file']
        project = form.cleaned_data['project']

        try:
            # Read Excel file
            df = pd.read_excel(excel_file, engine='openpyxl')

            # Validate required columns - requester is now required
            required_columns = ['title', 'description', 'status', 'severity', 'requester']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                messages.error(
                    self.request,
                    f"Missing required columns: {', '.join(missing_columns)}"
                )
                return self.form_invalid(form)

            # Process each row
            issues_created = 0
            for _, row in df.iterrows():
                # Skip rows with empty title
                if pd.isna(row['title']) or not row['title'].strip():
                    continue

                # CHECK FOR MANDATORY REQUESTER FIELD
                requester_username = row.get('requester')
                if pd.isna(requester_username) or not requester_username.strip():
                    messages.error(
                        self.request,
                        f"Row with title '{row['title']}' is missing required requester field"
                    )
                    return self.form_invalid(form)

                # Find the requester user
                try:
                    user_model = get_user_model()
                    requester = user_model.objects.get(username=requester_username.strip())
                except user_model.DoesNotExist:
                    messages.error(
                        self.request,
                        f"Requester '{requester_username}' not found in the system"
                    )
                    return self.form_invalid(form)

                # Create issue - WITHOUT solution field
                issue = Issue(
                    project=project,
                    title=row['title'],
                    description=row.get('description', '') if not pd.isna(row.get('description', '')) else '',
                    status=row.get('status', 'open') if not pd.isna(row.get('status', '')) else 'open',
                    severity=row.get('severity', 'medium') if not pd.isna(row.get('severity', '')) else 'medium',
                    requester=requester  # Use the found requester
                    # Removed solution field completely
                )

                # Handle assignee if present - IMPROVED LOGIC
                assignee_username = row.get('assignee')
                if assignee_username and not pd.isna(assignee_username) and assignee_username.strip():
                    try:
                        user_model = get_user_model()
                        assignee = user_model.objects.get(username=assignee_username.strip())
                        issue.assignee = assignee
                    except user_model.DoesNotExist:
                        # Log warning but don't fail the import
                        messages.warning(
                            self.request,
                            f"Assignee '{assignee_username}' not found for issue '{row['title']}' - leaving unassigned"
                        )

                issue.save()
                issues_created += 1

            messages.success(
                self.request,
                f"Successfully imported {issues_created} issues"
            )

        except Exception as e:
            messages.error(
                self.request,
                f"Error importing issues: {str(e)}"
            )
            return self.form_invalid(form)

        return super().form_valid(form)
