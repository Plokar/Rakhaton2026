from django.urls import path
from .views import ItemListView, item_detail

app_name = 'items'

urlpatterns = [
    path('', ItemListView.as_view(), name='list'),
    path('<int:pk>/', item_detail, name='detail'),
]
