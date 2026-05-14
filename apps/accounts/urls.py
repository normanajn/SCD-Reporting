from django.urls import path

from . import views

urlpatterns = [
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('admin-users/', views.AdminUsersView.as_view(), name='admin-users'),
    path('admin-users/create/',                  views.AdminCreateUserView.as_view(), name='user-create'),
    path('admin-users/signup-toggle/',           views.SignupToggleView.as_view(),    name='signup-toggle'),
    path('admin-users/<int:pk>/role/',           views.UserRoleUpdateView.as_view(),          name='user-role-update'),
    path('admin-users/<int:pk>/managed-groups/', views.UserManagedGroupsView.as_view(),       name='user-managed-groups'),
    path('admin-users/<int:pk>/set-password/',   views.UserSetPasswordView.as_view(), name='user-set-password'),
    path('admin-users/<int:pk>/delete/',         views.UserDeleteView.as_view(),      name='user-delete'),
]
