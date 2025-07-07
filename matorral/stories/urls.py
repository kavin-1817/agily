from django.urls import path

from .views import (
    EpicCreateView,
    EpicDetailView,
    EpicUpdateView,
    EpicList,
    StoryCreateView,
    StoryDetailView,
    StoryList,
    StoryUpdateView,
    upload_story_attachment,
    download_story_attachment,
)

app_name = "stories"

urlpatterns = [
    path("epics/add/", EpicCreateView.as_view(), name="epic-add"),
    path("epics/<int:pk>/edit/", EpicUpdateView.as_view(), name="epic-edit"),
    path("epics/<int:pk>/", EpicDetailView.as_view(), name="epic-detail"),
    path("epics/", EpicList.as_view(), name="epic-list"),
    path("stories/add/", StoryCreateView.as_view(), name="story-add"),
    path("stories/<int:pk>/edit/", StoryUpdateView.as_view(), name="story-edit"),
    path("stories/<int:pk>/", StoryDetailView.as_view(), name="story-detail"),
    path("stories/", StoryList.as_view(), name="story-list"),
    path('stories/<int:pk>/attachments/upload/', upload_story_attachment, name='story-attachment-upload'),
    path('attachment/<slug:workspace>/<int:pk>/download/', download_story_attachment, name='story-attachment-download'),
]
