from django.urls import path

from agily.health_checks.views import liveness, readiness

urlpatterns = [
    path("live/", liveness),
    path("ready/", readiness),
]
