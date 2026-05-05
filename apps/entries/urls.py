from django.urls import path

from . import views

app_name = 'entries'

urlpatterns = [
    path('',              views.EntryListView.as_view(),   name='list'),
    path('new/',          views.EntryCreateView.as_view(), name='create'),
    path('<int:pk>/',     views.EntryDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/',   views.EntryUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.EntryDeleteView.as_view(), name='delete'),
    path('period-prefill/',    views.PeriodPrefillView.as_view(),    name='period-prefill'),
    path('markdown-preview/',  views.MarkdownPreviewView.as_view(),  name='markdown-preview'),
]
