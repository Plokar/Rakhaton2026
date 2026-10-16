from django.urls import path

from . import views

urlpatterns = [
    path('me/', views.me, name='mdt-me'),
    path('sessions/', views.session_list, name='session-list'),
    path('sessions/<int:sid>/', views.session_detail, name='session-detail'),
    path('configs/', views.config_list, name='config-list'),
    path('configs/<int:cfg_id>/', views.config_detail, name='config-detail'),
    path('tasks/', views.task_list, name='task-list'),
    path('tasks/<str:tid>/', views.task_detail, name='task-detail'),
    path('patients/<str:pid>/intake/', views.patient_intake, name='patient-intake'),
    path('cases/', views.case_create, name='case-create'),
    path('cases/<int:cid>/', views.case_detail, name='case-detail'),
    path('cases/<int:cid>/decision/', views.case_decision, name='case-decision'),
    path('cases/<int:cid>/decision/confirm/', views.case_decision_confirm, name='case-decision-confirm'),
    path('cases/<int:cid>/export.fhir.json', views.case_export_fhir, name='case-export-fhir'),
    path('cases/<int:cid>/export.pdf', views.case_export_pdf, name='case-export-pdf'),
    path('cases/<int:cid>/brief/', views.case_brief, name='case-brief'),
    path('cases/<int:cid>/scribe/', views.case_scribe, name='case-scribe'),
    path('cases/<int:cid>/readiness/', views.case_readiness, name='case-readiness'),
    path('cases/<int:cid>/compatibility/', views.case_compatibility, name='case-compatibility'),
]
