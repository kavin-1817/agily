#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from agily.stories.forms import StoryForm, EpicForm
from agily.stories.models import Epic
from agily.sprints.models import Sprint
from agily.workspaces.models import Workspace

# Test the forms
print("Testing StoryForm and EpicForm querysets...")

# Get the first workspace
workspace = Workspace.objects.first()
if workspace:
    print(f"Testing with workspace: {workspace.slug}")
    
    # Test StoryForm
    story_form = StoryForm(workspace=workspace.slug)
    print(f"Epic queryset count: {story_form.fields['epic'].queryset.count()}")
    print(f"Sprint queryset count: {story_form.fields['sprint'].queryset.count()}")
    print(f"Project queryset count: {story_form.fields['project'].queryset.count()}")
    
    # Test EpicForm
    epic_form = EpicForm(workspace=workspace.slug)
    print(f"Owner queryset count: {epic_form.fields['owner'].queryset.count()}")
    
else:
    print("No workspaces found in database") 