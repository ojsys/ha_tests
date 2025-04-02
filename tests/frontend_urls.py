from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tests/', views.test_list, name='test-list'),
    path('tests/<int:test_id>/', views.test_detail, name='test-detail'),
    path('tests/<int:test_id>/take/', views.take_test, name='take-test'),
    path('tests/attempts/<int:attempt_id>/submit/', views.submit_test, name='submit-test'),
    path('tests/attempts/<int:attempt_id>/', views.attempt_detail, name='attempt-detail'),
    path('results/', views.results, name='results'),
]