from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Project, Issue, IssueAttachment
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Max, Case, When
from django.shortcuts import render, get_object_or_404, redirect
from .forms import IssueForm, IssueGlobalForm, ProjectForm, IssueAttachmentForm, IssueAttachmentFormSet, MultiIssueAttachmentForm
from django.http import HttpResponseForbidden, FileResponse
from django.contrib import messages
from django.db import models
import os
from django.utils.encoding import smart_str


class BaseListView(ListView):
    paginate_by = 16

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
        if "workspace" in self.kwargs:
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
class ProjectListView(ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        workspace_slug = self.request.session.get("current_workspace")
        if workspace_slug:
            return Project.objects.filter(workspace__slug=workspace_slug)
        return Project.objects.none()

@method_decorator([login_required, user_passes_test(lambda u: u.is_staff)], name="dispatch")
class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

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

@method_decorator(login_required, name="dispatch")
class IssueListView(ListView):
    model = Issue
    template_name = "projects/issue_list.html"
    context_object_name = "issues"

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        qs = Issue.objects.filter(project_id=project_id)
        issue_id = self.request.GET.get("id")
        if issue_id:
            qs = qs.filter(id=issue_id)
        # Order by severity: critical > high > medium > low, then by created_at desc
        severity_order = Case(
            When(severity="critical", then=0),
            When(severity="high", then=1),
            When(severity="medium", then=2),
            When(severity="low", then=3),
            default=4,
            output_field=models.IntegerField(),
        )
        return qs.order_by(severity_order, "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = get_object_or_404(Project, id=self.kwargs["project_id"])
        return context

@method_decorator(login_required, name="dispatch")
class IssueCreateView(CreateView):
    form_class = IssueForm
    template_name = "projects/issue_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        form.instance.project_id = self.kwargs["project_id"]
        response = super().form_valid(form)
        if attachment_form.is_valid():
            files = self.request.FILES.getlist("files")
            description = attachment_form.cleaned_data.get("description", "")
            for f in files:
                IssueAttachment.objects.create(issue=self.object, file=f, description=description)
        return response

    def get_success_url(self):
        return reverse_lazy("issue-list", kwargs={"project_id": self.kwargs["project_id"]})

@method_decorator(login_required, name="dispatch")
class IssueDetailView(DetailView):
    model = Issue
    template_name = "projects/issue_detail.html"
    context_object_name = "issue"

@method_decorator(login_required, name="dispatch")
class IssueGlobalListView(ListView):
    model = Issue
    template_name = "projects/issue_list.html"
    context_object_name = "issues"

    def get_queryset(self):
        qs = Issue.objects.all()
        issue_id = self.request.GET.get("id")
        if issue_id:
            qs = qs.filter(id=issue_id)
        severity_order = Case(
            When(severity="critical", then=0),
            When(severity="high", then=1),
            When(severity="medium", then=2),
            When(severity="low", then=3),
            default=4,
            output_field=models.IntegerField(),
        )
        return qs.order_by(severity_order, "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = None
        context["global_issues"] = True
        return context

@method_decorator(login_required, name="dispatch")
class IssueGlobalCreateView(CreateView):
    form_class = IssueGlobalForm
    template_name = "projects/issue_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
                IssueAttachment.objects.create(issue=self.object, file=f, description=description)
        return response

    def get_success_url(self):
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
    response = FileResponse(file_handle)
    filename = os.path.basename(attachment.file.name)
    response['Content-Disposition'] = f'attachment; filename="{smart_str(filename)}"'
    response['Content-Length'] = attachment.file.size
    return response

@login_required
def delete_issue_attachment(request, pk):
    attachment = get_object_or_404(IssueAttachment, pk=pk)
    issue = attachment.issue
    if request.method == "POST":
        attachment.delete()
        messages.success(request, "Attachment deleted successfully.")
        return redirect("issue-detail", project_id=issue.project_id, pk=issue.pk)
    return render(request, "projects/issue_attachment_confirm_delete.html", {"attachment": attachment})
