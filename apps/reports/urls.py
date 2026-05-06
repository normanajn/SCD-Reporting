from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('',                      views.ReportIndexView.as_view(),         name='index'),
    path('preview/',              views.ReportPreviewView.as_view(),        name='preview'),
    path('download/<str:fmt>/',   views.ReportDownloadView.as_view(),       name='download'),
    path('summary/',              views.ReportSummaryView.as_view(),        name='summary'),
    path('summary/download/txt/', views.SummaryDownloadTxtView.as_view(),   name='summary-download-txt'),
    path('summary/download/pdf/', views.SummaryDownloadPdfView.as_view(),   name='summary-download-pdf'),
    path('prompt-config/',        views.AIPromptConfigView.as_view(),       name='prompt-config'),
]
