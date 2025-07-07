from django.urls import path

from .views import WorkspaceCreateView, WorkspaceDetailView, WorkspaceList, WorkspaceUpdateView, WorkspaceSelectView

app_name = "workspaces"

urlpatterns = [
    path("add/", WorkspaceCreateView.as_view(), name="workspace-add"),
    path("<int:pk>/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("<int:pk>/edit/", WorkspaceUpdateView.as_view(), name="workspace-edit"),
    path("select/", WorkspaceSelectView.as_view(), name="workspace-select"),
    path("", WorkspaceList.as_view(), name="workspace-list"),
]
