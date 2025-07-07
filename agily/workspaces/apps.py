from django.apps import AppConfig
from django.db.models.signals import post_save


class WorkspacesConfig(AppConfig):
    name = "agily.workspaces"

    def ready(self):
        from agily.workspaces import signals
        from agily.users.models import User

        post_save.connect(signals.create_default_workspace, sender=User)
