from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('', views.TestListView.as_view(), name='test-list'),
    path('<int:pk>/', views.TestDetailView.as_view(), name='test-detail'),
    path('<int:test_id>/start/', views.StartTestView.as_view(), name='start-test'),
    path('attempts/<int:attempt_id>/answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('attempts/<int:attempt_id>/submit/', views.SubmitTestView.as_view(), name='submit-test'),
    path('attempts/', views.TestAttemptListView.as_view(), name='attempt-list'),
    path('attempts/<int:pk>/', views.TestAttemptDetailView.as_view(), name='attempt-detail'),
]