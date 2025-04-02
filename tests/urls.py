from django.urls import path
from . import views

app_name = 'tests'

urlpatterns = [
    path('tests/', views.TestListView.as_view(), name='test-list'),
    path('tests/<int:pk>/', views.TestDetailView.as_view(), name='test-detail'),
    path('tests/<int:test_id>/start/', views.StartTestView.as_view(), name='start-test'),
    path('tests/attempts/<int:attempt_id>/submit/', views.SubmitTestView.as_view(), name='submit-test'),
    path('tests/attempts/<int:attempt_id>/answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('tests/attempts/', views.TestAttemptListView.as_view(), name='attempt-list'),
    path('tests/attempts/<int:pk>/', views.TestAttemptDetailView.as_view(), name='attempt-detail'),


    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('test-list/', views.test_list, name='test-list'),
    path('tests/<int:test_id>/', views.test_detail, name='test-detail'),
    path('tests/<int:test_id>/take/', views.take_test, name='take-test'),
    path('tests/attempts/<int:attempt_id>/submit/', views.submit_test, name='submit-test'),
    path('tests/attempts/<int:attempt_id>/', views.attempt_detail, name='attempt-detail'),
    path('results/', views.results, name='results'),
]