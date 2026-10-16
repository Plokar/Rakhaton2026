from django.urls import path

from . import views

urlpatterns = [
    path('sessions/', views.session_list, name='session-list'),
    path('sessions/<int:sid>/', views.session_detail, name='session-detail'),
    path('cases/<int:cid>/brief/', views.case_brief, name='case-brief'),
]
