from django.conf import settings
from django.urls import include, path, re_path
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views import defaults as default_views
from django.http import HttpResponse

from agily.workspaces.views import workspace_index
from agily.users.views import CustomLoginView, CustomLogoutView, UserRegisterView
# Add these lines to the imports at the top
from agily.views import (
    ProjectListView, ProjectCreateView, ProjectDetailView, IssueGlobalListView, IssueGlobalCreateView,
    upload_issue_attachment, download_issue_attachment, delete_issue_attachment, ProjectUpdateView, 
    IssueGlobalUpdateView, IssueGlobalDetailView, IssueGlobalDeleteView, ProjectDeleteView, public_test_view,
    IssueExportView, IssueImportView  # Add these two imports
)

# Add these to your urlpatterns
from agily.stories.views import StoryDeleteView, EpicDeleteView


urlpatterns = [
    # Django Admin, use {% url 'admin:index' %}
    re_path(settings.ADMIN_URL, admin.site.urls),
    # health checks
    re_path(r"^health/", include("agily.health_checks.urls")),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    # User management
    re_path(r"^users/", include("agily.users.urls")),
    path('signup/', UserRegisterView.as_view(), name='signup'),
    # App
    path('dashboard/', include('dashboard.urls')),
    path("projects/", ProjectListView.as_view(), name="project-list"),
    path("projects/add/", ProjectCreateView.as_view(), name="project-add"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<int:pk>/edit/", ProjectUpdateView.as_view(), name="project-edit"),
    path("projects/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project-delete"),
    path("issues/", IssueGlobalListView.as_view(), name="global-issue-list"),
    path("issues/add/", IssueGlobalCreateView.as_view(), name="global-issue-add"),
    path("issues/<int:pk>/edit/", IssueGlobalUpdateView.as_view(), name="global-issue-edit"),
    path("issues/<int:pk>/", IssueGlobalDetailView.as_view(), name="global-issue-detail"),
    path("issues/<int:pk>/delete/", IssueGlobalDeleteView.as_view(), name="global-issue-delete"),
    path("issues/attachment/<int:pk>/delete/", delete_issue_attachment, name="delete-issue-attachment"),
    path("issues/attachment/<int:pk>/download/", download_issue_attachment, name="download-issue-attachment"),
    path("issues/<int:pk>/attachments/upload/", upload_issue_attachment, name="upload-issue-attachment"),
    path(r"<workspace>/", include("agily.stories.urls", namespace="stories")),
    path(r"<workspace>/sprints/", include("agily.sprints.urls", namespace="sprints")),
    path(r"<workspace>/stories/<int:pk>/delete/", StoryDeleteView.as_view(), name="stories:story-delete"),
    path(r"<workspace>/epics/<int:pk>/delete/", EpicDeleteView.as_view(), name="stories:epic-delete"),
    path("workspaces/", include("agily.workspaces.urls", namespace="workspaces")),
    path(r"", workspace_index, name="workspace_index"),  # disabled for now, until we finish all the features
    # Workspace-aware Issues
    path("<workspace>/issues/", IssueGlobalListView.as_view(), name="workspace-issue-list"),
    # Add these two lines
    path("<workspace>/issues/export/", IssueExportView.as_view(), name="workspace-issue-export"),
    path("<workspace>/issues/import/", IssueImportView.as_view(), name="workspace-issue-import"),
    path("<workspace>/issues/add/", IssueGlobalCreateView.as_view(), name="workspace-issue-add"),
    path("<workspace>/issues/<int:pk>/edit/", IssueGlobalUpdateView.as_view(), name="workspace-issue-edit"),
    path("<workspace>/issues/<int:pk>/", IssueGlobalDetailView.as_view(), name="workspace-issue-detail"),
    path("<workspace>/issues/<int:pk>/delete/", IssueGlobalDeleteView.as_view(), name="workspace-issue-delete"),
    path('test-public/', public_test_view, name='public-test'),
    path('signup-test/', lambda request: HttpResponse('Signup test view works.'), name='signup-test'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}),
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")}),
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
        path("500/", default_views.server_error),
    ]
