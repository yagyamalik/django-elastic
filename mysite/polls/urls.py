from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload_document/', views.upload_document, name='upload_document'),
    path('initiate_index/', views.initiate_index, name='initiate_index'),
    path('search/', views.search, name='search'),
]