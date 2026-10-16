from django.urls import path

from . import views

urlpatterns = [
    path('', views.patient_list, name='patient-list'),
    path('<str:pid>/', views.patient_detail, name='patient-detail'),
    path('<str:pid>/timeline/', views.patient_timeline, name='patient-timeline'),
    path('<str:pid>/observations/', views.patient_observations, name='patient-observations'),
]
