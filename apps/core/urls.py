from django.urls import path

from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/summary/',              views.DashboardSummaryView.as_view(),            name='dashboard-summary'),
    path('dashboard/summary/download/txt/', views.DashboardSummaryDownloadTxtView.as_view(), name='dashboard-summary-txt'),
    path('dashboard/summary/download/md/',  views.DashboardSummaryDownloadMdView.as_view(),  name='dashboard-summary-md'),
    path('dashboard/summary/download/pdf/', views.DashboardSummaryDownloadPdfView.as_view(), name='dashboard-summary-pdf'),
    path('dashboard/prompt-config/',        views.DashboardPromptConfigView.as_view(),        name='dashboard-prompt-config'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('bug-report/', views.BugReportView.as_view(), name='bug-report'),
    path('bug-report/submit/', views.BugReportSubmitView.as_view(), name='bug-report-submit'),
]
