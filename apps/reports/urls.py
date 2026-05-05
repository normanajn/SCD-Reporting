from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('',                    views.ReportIndexView.as_view(),    name='index'),
    path('preview/',            views.ReportPreviewView.as_view(),  name='preview'),
    path('download/<str:fmt>/', views.ReportDownloadView.as_view(), name='download'),
]
