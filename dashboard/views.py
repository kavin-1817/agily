from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from agily.models import Project, Issue
from agily.stories.models import Story
from agily.sprints.models import Sprint
from agily.workspaces.models import Workspace

@login_required
def dashboard_view(request):
    """Main dashboard view that routes to appropriate dashboard based on user role"""
    user = request.user
    group_names = [g.name.lower().strip() for g in user.groups.all()]
    
    # Debug: Add this temporarily to see what groups the user has
    print(f"User: {user.username}")
    print(f"Groups: {group_names}")
    
    # Get current workspace
    workspace_slug = request.session.get("current_workspace")
    current_workspace = None
    if workspace_slug:
        try:
            current_workspace = Workspace.objects.get(slug=workspace_slug)
        except Workspace.DoesNotExist:
            pass
    
    # Check role detection
    if user.is_superuser:
        print("Rendering superuser dashboard")
        return render_superuser_dashboard(request, current_workspace)
    elif "project admin" in group_names:
        print("Rendering project admin dashboard")
        return render_project_admin_dashboard(request, current_workspace)
    elif any(g in ["developer", "developers"] for g in group_names):
        print("Rendering developer dashboard")
        return render_developer_dashboard(request, current_workspace)
    elif any(g in ["tester", "testers"] for g in group_names):
        print("Rendering tester dashboard")
        return render_tester_dashboard(request, current_workspace)
    else:
        print("Rendering default dashboard")
        return render_default_dashboard(request, current_workspace)


def render_superuser_dashboard(request, workspace):
    """Dashboard for superusers with system-wide statistics"""
    
    # Get base querysets
    if workspace:
        projects = Project.objects.filter(workspace=workspace)
        issues = Issue.objects.filter(project__workspace=workspace)
        stories = Story.objects.filter(project__workspace=workspace)
        sprints = Sprint.objects.filter(project__workspace=workspace)
    else:
        projects = Project.objects.all()
        issues = Issue.objects.all()
        stories = Story.objects.all()
        sprints = Sprint.objects.all()
    
    # Statistics
    stats = {
        'total_projects': projects.count(),
        'total_issues': issues.count(),
        'total_stories': stories.count(),
        'total_sprints': sprints.count(),
        
        'pending_issues': issues.filter(status='open').count(),
        'resolved_issues': issues.filter(status='resolved').count(),
        'closed_issues': issues.filter(status='closed').count(),
        
        'critical_issues': issues.filter(severity='critical').count(),
        'high_issues': issues.filter(severity='high').count(),
        
        'pending_stories': stories.filter(state__stype=0).count(),  # STATE_UNSTARTED
        'in_progress_stories': stories.filter(state__stype=1).count(),  # STATE_STARTED
        'completed_stories': stories.filter(state__stype=2).count(),  # STATE_DONE
    }
    
    # Recent activities (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_issues = issues.filter(created_at__gte=week_ago).order_by('-created_at')[:5]
    recent_stories = stories.filter(created_at__gte=week_ago).order_by('-created_at')[:5]
    
    # Projects by status
    project_stats = []
    for project in projects[:10]:  # Limit to 10 projects
        project_issues = issues.filter(project=project)
        project_stories = stories.filter(project=project)
        project_stats.append({
            'project': project,
            'issues_count': project_issues.count(),
            'stories_count': project_stories.count(),
            'pending_issues': project_issues.filter(status='open').count(),
            'pending_stories': project_stories.filter(state__stype=0).count(),
        })
    
        context = {
        'user_role': 'Superuser',
        'stats': stats,
        'recent_issues': recent_issues,
        'recent_stories': recent_stories,
        'project_stats': project_stats,
        'current_workspace': workspace,  # ✅ This is good
        'current_workspace': workspace,  # Add this line to ensure it's available for navigation
    }
    
    return render(request, 'dashboard/superuser_dashboard.html', context)

def render_project_admin_dashboard(request, workspace):
    """Dashboard for project admins"""
    user = request.user
    
    # Get projects managed by this admin and related data
    if workspace:
        managed_projects = Project.objects.filter(project_admin=user, workspace=workspace)
        all_issues = Issue.objects.filter(project__workspace=workspace, project__project_admin=user)
        all_stories = Story.objects.filter(project__workspace=workspace, project__project_admin=user)
    else:
        managed_projects = Project.objects.filter(project_admin=user)
        all_issues = Issue.objects.filter(project__project_admin=user)
        all_stories = Story.objects.filter(project__project_admin=user)
    
    stats = {
        'managed_projects': managed_projects.count(),
        'total_issues': all_issues.count(),
        'total_stories': all_stories.count(),
        'pending_issues': all_issues.filter(status='open').count(),
        'resolved_issues': all_issues.filter(status='resolved').count(),
        'closed_issues': all_issues.filter(status='closed').count(),
        'critical_issues': all_issues.filter(severity='critical').count(),
        'pending_stories': all_stories.filter(state__stype=0).count(),
        'in_progress_stories': all_stories.filter(state__stype=1).count(),
        'completed_stories': all_stories.filter(state__stype=2).count(),
    }
    
    # Recent activities in managed projects
    week_ago = timezone.now() - timedelta(days=7)
    recent_issues = all_issues.filter(created_at__gte=week_ago).order_by('-created_at')[:5]
    recent_stories = all_stories.filter(created_at__gte=week_ago).order_by('-created_at')[:5]
    
    context = {
        'user_role': 'Project Admin',
        'stats': stats,
        'recent_issues': recent_issues,
        'recent_stories': recent_stories,
        'current_workspace': workspace,
    }
    
    return render(request, 'dashboard/project_admin_dashboard.html', context)



def render_developer_dashboard(request, workspace):
    """Dashboard for developers"""
    user = request.user
    
    # Get assigned issues and stories
    if workspace:
        assigned_issues = Issue.objects.filter(assignee=user, project__workspace=workspace)
        assigned_stories = Story.objects.filter(assignee=user, project__workspace=workspace)
    else:
        assigned_issues = Issue.objects.filter(assignee=user)
        assigned_stories = Story.objects.filter(assignee=user)
    
    # Calculate statistics
    total_assigned_issues = assigned_issues.count()
    total_assigned_stories = assigned_stories.count()
    open_issues = assigned_issues.filter(status='open').count()
    resolved_issues = assigned_issues.filter(status='resolved').count()
    pending_stories = assigned_stories.filter(state__stype=0).count()
    in_progress_stories = assigned_stories.filter(state__stype=1).count()
    completed_stories = assigned_stories.filter(state__stype=2).count()
    critical_issues = assigned_issues.filter(severity='critical').count()
    
    # Calculate progress percentages
    issues_progress = int((resolved_issues * 100 / total_assigned_issues)) if total_assigned_issues > 0 else 0
    stories_progress = int((completed_stories * 100 / total_assigned_stories)) if total_assigned_stories > 0 else 0
    
    stats = {
        'assigned_issues': total_assigned_issues,
        'assigned_stories': total_assigned_stories,
        'open_issues': open_issues,
        'resolved_issues': resolved_issues,
        'pending_stories': pending_stories,
        'in_progress_stories': in_progress_stories,
        'completed_stories': completed_stories,
        'critical_issues': critical_issues,
        'issues_progress': issues_progress,
        'stories_progress': stories_progress,
    }
    
    # Recent assignments
    week_ago = timezone.now() - timedelta(days=7)
    recent_issues = assigned_issues.filter(updated_at__gte=week_ago).order_by('-updated_at')[:5]
    recent_stories = assigned_stories.filter(updated_at__gte=week_ago).order_by('-updated_at')[:5]
    
    context = {
        'user_role': 'Developer',
        'stats': stats,
        'assigned_issues': assigned_issues.filter(status='open')[:10],
        'assigned_stories': assigned_stories.exclude(state__stype=2)[:10],  # Not completed
        'recent_issues': recent_issues,
        'recent_stories': recent_stories,
        'current_workspace': workspace,
    }
    
    return render(request, 'dashboard/developer_dashboard.html', context)


def render_tester_dashboard(request, workspace):
    """Dashboard for testers"""
    user = request.user
    
    # Get issues created by tester and stories assigned to tester
    if workspace:
        created_issues = Issue.objects.filter(requester=user, project__workspace=workspace)
        assigned_stories = Story.objects.filter(assignee=user, project__workspace=workspace)
        all_issues = Issue.objects.filter(project__workspace=workspace)
        all_stories = Story.objects.filter(project__workspace=workspace)
    else:
        created_issues = Issue.objects.filter(requester=user)
        assigned_stories = Story.objects.filter(assignee=user)
        all_issues = Issue.objects.all()
        all_stories = Story.objects.all()
    
    # Calculate issue status counts
    open_issues_created = created_issues.filter(status='open').count()
    resolved_issues_created = created_issues.filter(status='resolved').count()
    closed_issues_created = created_issues.filter(status='closed').count()
    
    stats = {
        'created_issues': created_issues.count(),
        'assigned_stories': assigned_stories.count(),
        
        # Issue status breakdown for issues created by tester
        'open_issues': open_issues_created,
        'resolved_issues': resolved_issues_created,
        'closed_issues': closed_issues_created,
        
        # Story status
        'pending_stories': assigned_stories.filter(state__stype=0).count(),
        'in_progress_stories': assigned_stories.filter(state__stype=1).count(),
        'completed_stories': assigned_stories.filter(state__stype=2).count(),
        
        # Overall system stats
        'total_open_issues': all_issues.filter(status='open').count(),
        'critical_issues': all_issues.filter(severity='critical').count(),
    }
    
    # Recent activities
    week_ago = timezone.now() - timedelta(days=7)
    recent_issues = created_issues.filter(created_at__gte=week_ago).order_by('-created_at')[:5]
    recent_stories = assigned_stories.filter(updated_at__gte=week_ago).order_by('-updated_at')[:5]
    
    context = {
        'user_role': 'Tester',
        'stats': stats,
        'created_issues': created_issues.filter(status='open')[:10],
        'assigned_stories': assigned_stories.exclude(state__stype=2)[:10],  # Not completed
        'recent_issues': recent_issues,
        'recent_stories': recent_stories,
        'current_workspace': workspace,
    }
    
    return render(request, 'dashboard/tester_dashboard.html', context)
