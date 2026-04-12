from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.index,          name='index'),
    path('recommend/',        views.recommend,      name='recommend'),
    path('api/recommend/',    views.api_recommend,  name='api_recommend'),
    path('api/waiting/',      views.api_waiting,    name='api_waiting'),
    path('api/check_region/', views.api_check_region, name='api_check_region'),
    path('api/chat/',         views.api_chat,       name='api_chat'),
]
