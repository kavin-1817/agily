from urllib.parse import parse_qsl

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy, reverse, NoReverseMatch
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import render, redirect

from ..utils import get_clean_next_url
from .models import Workspace
from .tasks import duplicate_workspaces, remove_workspaces


@method_decorator(login_required, name="dispatch")
class WorkspaceDetailView(DetailView):

    model = Workspace

    def get_children(self):
        return self.get_object().members.order_by("username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["objects_by_group"] = [(None, self.get_children())]
        context["current_workspace"] = self.kwargs["workspace"]
        return context

    def post(self, *args, **kwargs):
        params = dict(parse_qsl(self.request.body.decode("utf-8")))
        url = self.request.get_full_path()

        if params.get("remove") == "yes":
            remove_workspaces.delay([self.get_object().id])
            url = reverse_lazy("workspaces:workspace-list", args=[kwargs["workspace"]])

        if self.request.headers.get("X-Fetch") == "true":
            return JsonResponse(dict(url=url))
        else:
            return HttpResponseRedirect(url)


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
                params["name__icontains"] = part

        return params

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.GET.get("q") is not None:
            context["show_all_url"] = self.request.path

        context["title"] = self.model._meta.verbose_name_plural.capitalize()
        context["singular_title"] = self.model._meta.verbose_name.capitalize()
        context["current_workspace"] = self.kwargs["workspace"]

        return context

    def get_queryset(self):
        qs = self.model.objects

        q = self.request.GET.get("q")

        params = self._build_filters(q)

        if q is None:
            qs = qs.all()
        else:
            qs = qs.filter(**params)

        if self.select_related is not None:
            qs = qs.select_related(*self.select_related)

        if self.prefetch_related is not None:
            qs = qs.prefetch_related(*self.prefetch_related)

        return qs


@method_decorator(login_required, name="dispatch")
class WorkspaceList(BaseListView):
    model = Workspace

    filter_fields = dict(owner="owner__username")

    select_related = None
    prefetch_related = None

    def get_queryset(self):
        return super().get_queryset().all()

    def post(self, *args, **kwargs):
        params = dict(parse_qsl(self.request.body.decode("utf-8")))

        workspace_ids = [t.split("workspace-")[1] for t in params.keys() if "workspace-" in t]

        if len(workspace_ids) > 0:
            if params.get("remove") == "yes":
                remove_workspaces.delay(workspace_ids)

            if params.get("duplicate") == "yes":
                duplicate_workspaces.delay(workspace_ids)

        url = self.request.get_full_path()

        if self.request.headers.get("X-Fetch") == "true":
            return JsonResponse(dict(url=url))
        else:
            return HttpResponseRedirect(url)


class WorkspaceBaseView:
    model = Workspace
    fields = ["name", "description"]

    @property
    def success_url(self):
        return get_clean_next_url(self.request, reverse_lazy("workspaces:workspace-list"))

    def form_valid(self, form):
        response = super().form_valid(form)

        url = self.get_success_url()

        if self.request.headers.get("X-Fetch") == "true":
            return JsonResponse(dict(url=url))

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.kwargs.get("workspace")
        if workspace:
            workspace_add_url = reverse_lazy("workspaces:workspace-add", args=[workspace])
            context["workspace_add_url"] = workspace_add_url
            context["current_workspace"] = workspace
        return context


@method_decorator(login_required, name="dispatch")
class WorkspaceCreateView(WorkspaceBaseView, CreateView):

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.slug = slugify(form.data.get("name", ""))
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class WorkspaceUpdateView(WorkspaceBaseView, UpdateView):

    def post(self, *args, **kwargs):
        data = dict(parse_qsl(self.request.body.decode("utf-8")))

        if data.get("save-as-new"):
            form = self.get_form_class()(data)
        else:
            form = self.get_form_class()(data, instance=self.get_object())

        return self.form_valid(form)


@login_required
def workspace_index(request):
    default_workspace = request.user.workspace_set.order_by("id").first()
    if not default_workspace:
        # Redirect to workspace creation page if user has no workspaces
        return HttpResponseRedirect(reverse_lazy("workspaces:workspace-add"))
    request.session["current_workspace"] = default_workspace.slug
    return HttpResponseRedirect(reverse_lazy("stories:story-list", args=[default_workspace.slug]))


class WorkspaceSelectView(ListView):
    model = Workspace
    template_name = "workspaces/workspace_select.html"
    context_object_name = "workspaces"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"workspaces": Workspace.objects.all()})

    def post(self, request, *args, **kwargs):
        workspace_slug = request.POST.get("workspace")
        print("[DEBUG] POST data:", request.POST)
        print("[DEBUG] Selected workspace_slug:", workspace_slug)
        try:
            if workspace_slug:
                request.session["current_workspace"] = workspace_slug
                print("[DEBUG] Set session current_workspace to:", workspace_slug)
                # Try to reverse the URL and print it
                try:
                    url = reverse("stories:story-list", kwargs={"workspace": workspace_slug})
                    print(f"[DEBUG] Redirecting to: {url}")
                except NoReverseMatch as e:
                    print(f"[ERROR] NoReverseMatch: {e}")
                    return render(request, self.template_name, {"workspaces": Workspace.objects.all(), "error": f"URL error: {e}"})
                return redirect("stories:story-list", workspace=workspace_slug)
            print("[DEBUG] No workspace selected, re-rendering form with error.")
            return render(request, self.template_name, {"workspaces": Workspace.objects.all(), "error": "Please select a workspace."})
        except Exception as e:
            print(f"[ERROR] Exception in WorkspaceSelectView.post: {e}")
            return render(request, self.template_name, {"workspaces": Workspace.objects.all(), "error": f"Exception: {e}"})
