# Add these to your existing URL patterns

# For global issue list
path("issues/export/", views.IssueExportView.as_view(), name="global-issue-export"),
path("issues/import/", views.IssueImportView.as_view(), name="global-issue-import"),

# For workspace issue list
path(
    "workspaces/<slug:workspace>/issues/export/",
    views.IssueExportView.as_view(),
    name="workspace-issue-export"
),
path(
    "workspaces/<slug:workspace>/issues/import/",
    views.IssueImportView.as_view(),
    name="workspace-issue-import"
),