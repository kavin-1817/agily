from django.contrib import admin
from .models import Project, Issue, Notification

admin.site.site_header = 'Agily Administration'
admin.site.site_title = 'Agily Administration'
admin.site.index_title = 'Welcome to Agily Administration'

class IssueAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "severity", "requester", "assignee", "created_at")
    list_filter = ("status", "severity", "project")
    search_fields = ("title", "description")

admin.site.register(Project)
admin.site.register(Issue, IssueAdmin)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'link', 'read', 'created_at')
    list_filter = ('read', 'created_at', 'user')
    search_fields = ('message', 'link')
    list_per_page = 25
    list_editable = ('read',)

admin.site.register(Notification, NotificationAdmin)