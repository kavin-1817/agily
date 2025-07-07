from django.contrib import admin
from .models import Project, Issue

class IssueAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "severity", "requester", "assignee", "created_at")
    list_filter = ("status", "severity", "project")
    search_fields = ("title", "description")

admin.site.register(Project)
admin.site.register(Issue, IssueAdmin) 