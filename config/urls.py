from django.conf import settings
from django.urls import include, path, re_path
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views import defaults as default_views

from agily.workspaces.views import workspace_index
from agily.views import (
    ProjectListView, ProjectCreateView, ProjectDetailView, IssueListView, IssueCreateView, IssueDetailView, IssueGlobalListView, IssueGlobalCreateView,
    upload_issue_attachment, download_issue_attachment, delete_issue_attachment
)


urlpatterns = [
    # Django Admin, use {% url 'admin:index' %}
    re_path(settings.ADMIN_URL, admin.site.urls),
    # health checks
    re_path(r"^health/", include("agily.health_checks.urls")),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), {"next_page": "/"}, name="logout"),
    # User management
    re_path(r"^users/", include("agily.users.urls")),
    # App
    path(r"<workspace>/", include("agily.stories.urls", namespace="stories")),
    path(r"<workspace>/sprints/", include("agily.sprints.urls", namespace="sprints")),
    path("workspaces/", include("agily.workspaces.urls", namespace="workspaces")),
    path(r"", workspace_index, name="workspace_index"),  # disabled for now, until we finish all the features
    path("projects/", ProjectListView.as_view(), name="project-list"),
    path("projects/add/", ProjectCreateView.as_view(), name="project-add"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<int:project_id>/issues/", IssueListView.as_view(), name="issue-list"),
    path("projects/<int:project_id>/issues/add/", IssueCreateView.as_view(), name="issue-add"),
    path("projects/<int:project_id>/issues/<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("issues/", IssueGlobalListView.as_view(), name="global-issue-list"),
    path("issues/add/", IssueGlobalCreateView.as_view(), name="global-issue-add"),
    path("issues/<int:pk>/attachments/upload/", upload_issue_attachment, name="upload-issue-attachment"),
    path("issues/attachment/<int:pk>/download/", download_issue_attachment, name="download-issue-attachment"),
    path("issues/attachment/<int:pk>/delete/", delete_issue_attachment, name="delete-issue-attachment"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    import debug_toolbar

    urlpatterns = [  # prepend
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

    urlpatterns += [
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}),
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")}),
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
        path("500/", default_views.server_error),
    ]
