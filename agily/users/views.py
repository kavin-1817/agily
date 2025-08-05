from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib.auth import login
from .forms import UserRegistrationForm
from django.views.generic.edit import FormView
import logging

from .models import User


class CustomLoginView(DjangoLoginView):
    """
    Custom login view that provides better error handling and user experience.
    """
    template_name = 'registration/login.html'
    form_class = AuthenticationForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_main_menu'] = True
        return context
    
    def form_invalid(self, form):
        """
        Handle invalid form submission with better error messages.
        """
        # Add a custom error message for authentication failures
        if not form.non_field_errors():
            form.add_error(None, "Invalid username or password. Please try again.")
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        """
        Redirect to the appropriate page after successful login.
        """
        # Check if there's a next parameter
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        
        # Default redirect to workspace index or dashboard
        return reverse('workspace_index')


class CustomLogoutView(DjangoLogoutView):
    """
    Custom logout view that handles logout more gracefully.
    """
    next_page = '/login/'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Clear any workspace session data before logout.
        """
        if 'current_workspace' in request.session:
            del request.session['current_workspace']
        return super().dispatch(request, *args, **kwargs)


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = "username"
    slug_url_kwarg = "username"


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = [
        "name",
    ]

    # we already imported User in the view code above, remember?
    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})

    def get_object(self):
        # Only get the User record for the user making the request
        return User.objects.get(username=self.request.user.username)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = "username"
    slug_url_kwarg = "username"


logger = logging.getLogger(__name__)

class UserRegisterView(FormView):
    form_class = UserRegistrationForm
    template_name = 'registration/register.html'
    success_url = '/'

    def dispatch(self, request, *args, **kwargs):
        logger.warning('UserRegisterView dispatch called: method=%s, path=%s, user=%s', request.method, request.path, request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, 'Registration successful! Please log in.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('login')
