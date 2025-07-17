from django.apps import apps
from django.db import models
from django.utils import timezone
from django.conf import settings
from agily.workspaces.models import Workspace


class BaseModel(models.Model):
    class Meta:
        abstract = True

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now=True, db_index=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    def is_done(self):
        return self.state.stype == self.state.STATE_DONE

    def save(self, *args, **kwargs):
        if self.is_done():
            self.completed_at = timezone.now()
        else:
            self.completed_at = None

        super().save(*args, **kwargs)


class ModelWithProgress(models.Model):
    class Meta:
        abstract = True

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now=True, db_index=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    total_points = models.PositiveIntegerField(default=0)
    story_count = models.PositiveIntegerField(default=0)
    points_done = models.PositiveIntegerField(default=0)
    progress = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def update_points_and_progress(self, save=True):
        Story = apps.get_model("stories", "Story")
        StoryState = apps.get_model("stories", "StoryState")

        parent_dict = {self._meta.model_name: self.id}

        # calculate total points
        total_points = Story.objects.filter(**parent_dict).aggregate(models.Sum("points"))["points__sum"] or 0

        if total_points == 0:
            # if no story has points, then count the stories
            total_points = Story.objects.filter(**parent_dict).count()

        # calculate points done
        params = parent_dict.copy()
        params["state__stype"] = StoryState.STATE_DONE
        points_done = Story.objects.filter(**params).aggregate(models.Sum("points"))["points__sum"] or 0

        if points_done == 0:
            # if no story has points, then count the stories
            points_done = Story.objects.filter(**params).count()

        self.total_points = total_points
        self.points_done = points_done
        self.story_count = Story.objects.filter(**parent_dict).count()

        self.progress = int(float(points_done) / (total_points or 1) * 100)

        if save:
            self.save()


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    project_admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name="administered_projects")

    class Meta:
        unique_together = ['name', 'workspace']

    def __str__(self):
        return self.name


class Issue(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="medium")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_issues")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_issues")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    solution = models.TextField(blank=True, null=True, help_text="Solution provided by the developer.")

    def __str__(self):
        return self.title


class IssueAttachment(models.Model):
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="issue_attachments/%Y/%m/%d/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.file:
            return self.file.name.split("/")[-1]
        return ""

    def filename(self):
        if self.file:
            return self.file.name.split("/")[-1]
        return ""

    def get_absolute_url(self):
        return self.file.url
