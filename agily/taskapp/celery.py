import os

import environ

from celery import Celery

from django.apps import AppConfig
from django.conf import settings


env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env("config/settings/.env")  # reading .env file

if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")  # pragma: no cover


app = Celery("agily")


class CeleryConfig(AppConfig):
    name = "agily.taskapp"
    verbose_name = "Celery Config"

    def ready(self):
        # Using a string here means the worker will not have to
        # pickle the object when using Windows.
        app.config_from_object("django.conf:settings")
        app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, force=True)
        app.conf.task_always_eager = settings.CELERY_ALWAYS_EAGER


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")  # pragma: no cover
