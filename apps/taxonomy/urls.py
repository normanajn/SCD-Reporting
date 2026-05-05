from django.urls import path

from . import views

app_name = 'taxonomy'

urlpatterns = [
    path('projects/', views.ProjectManageView.as_view(), name='projects'),
    path('projects/<int:pk>/edit/', views.ProjectEditView.as_view(), name='project-edit'),
    path('categories/', views.CategoryManageView.as_view(), name='categories'),
    path('categories/<int:pk>/edit/', views.CategoryEditView.as_view(), name='category-edit'),
    path('tags/autocomplete/', views.TagAutocompleteView.as_view(), name='tag-autocomplete'),
]
