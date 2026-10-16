from django.urls import path

from . import views

urlpatterns = [
    path('cases/<int:cid>/brief/', views.case_brief, name='case-brief'),
]
