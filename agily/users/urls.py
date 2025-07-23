from django.urls import path
from django.http import HttpResponse

from . import views

app_name = "users"
urlpatterns = [
    path("", view=views.UserListView.as_view(), name="list"),
    path("redirect/", view=views.UserRedirectView.as_view(), name="redirect"),
    path("<slug:username>/", view=views.UserDetailView.as_view(), name="detail"),
    path("update/", view=views.UserUpdateView.as_view(), name="update"),
    path("signup/", lambda request: HttpResponse('Signup test view works.'), name="signup"),
]
