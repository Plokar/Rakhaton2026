from django.urls import path

from . import views

urlpatterns = [
    path('me/', views.me, name='mdt-me'),
    path('sessions/', views.session_list, name='session-list'),
    path('sessions/<int:sid>/', views.session_detail, name='session-detail'),
    path('configs/', views.config_list, name='config-list'),
    path('configs/<int:cfg_id>/', views.config_detail, name='config-detail'),
    path('cases/<int:cid>/', views.case_detail, name='case-detail'),
    path('cases/<int:cid>/decision/', views.case_decision, name='case-decision'),
    path('cases/<int:cid>/decision/confirm/', views.case_decision_confirm, name='case-decision-confirm'),
    path('cases/<int:cid>/brief/', views.case_brief, name='case-brief'),
]
