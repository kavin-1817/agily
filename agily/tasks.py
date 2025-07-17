from agily.taskapp.celery import app
from agily.models import Project

@app.task(ignore_result=True)
def remove_projects(project_ids):
    Project.objects.filter(id__in=project_ids).delete() 