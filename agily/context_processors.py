from urllib.parse import quote_plus, unquote_plus

from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject

from .forms import SearchForm


def site(request):
    return dict(
        current_site=SimpleLazyObject(lambda: get_current_site(request)),
    )


def navigation(request):
    params = dict(encoded_url=quote_plus(request.get_full_path()), next_url=unquote_plus(request.GET.get("next", "")))

    try:
        params["page"] = int(request.GET.get("page", 0))
    except ValueError:
        pass

    get_vars = request.GET.copy()
    try:
        get_vars.pop("page")
    except KeyError:
        pass

    params["get_vars"] = "&" + get_vars.urlencode()

    return params


def search(request):
    return dict(search_form=SearchForm(request.GET))


def current_workspace(request):
    workspace_slug = request.session.get("current_workspace")
    return {"current_workspace": workspace_slug}


def user_roles(request):
    group_names = []
    user = getattr(request, 'user', None)
    if user and hasattr(user, 'groups'):
        group_names = [g.name.lower().strip() for g in user.groups.all()]
    return {
        'is_tester': any(g in ['tester', 'testers'] for g in group_names),
        'is_developer': any(g in ['developer', 'developers'] for g in group_names),
        'is_project_admin': 'project admin' in group_names,
    }
def dashboard_stats(request):
    """Add dashboard-specific context"""
    if not request.user.is_authenticated:
        return {}
    
    workspace_slug = request.session.get("current_workspace")
    context = {'current_workspace_slug': workspace_slug}
    
    return context


def notifications(request):
    """Add notification count to context"""
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}
    
    from .models import Notification
    count = Notification.objects.filter(user=request.user, read=False).count()
    return {"unread_notifications_count": count}
