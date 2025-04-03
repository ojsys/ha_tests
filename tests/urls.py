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
    path('test/<uuid:test_id>/start/', views.start_test, name='start-test'),
    # This should match the URL pattern you're trying to redirect to
    path('attempt/<uuid:attempt_id>/', views.take_test, name='take-test'),
    path('attempt/<uuid:attempt_id>/results/', views.test_results, name='test-results'),
    path('attempt/<uuid:attempt_id>/time-remaining/', views.get_time_remaining, name='time-remaining'),
    path('tests/attempts/<int:attempt_id>/submit/', views.submit_test, name='submit-test'),
    # Update these patterns to accept UUIDs instead of integers
    path('tests/attempts/<uuid:attempt_id>/', views.attempt_detail, name='attempt-detail'),
    
    
    # Make sure your other URL patterns that use UUIDs are also updated
    path('tests/<uuid:test_id>/', views.test_detail, name='test-detail'),
    path('tests/<uuid:test_id>/start/', views.start_test, name='start-test'),
    path('tests/<uuid:test_id>/edit/', views.edit_test, name='edit-test'),
    path('tests/<uuid:test_id>/toggle-status/', views.toggle_test_status, name='toggle-test-status'),
    path('tests/<uuid:test_id>/upload-questions/', views.upload_questions, name='upload-questions'),
    
    # For test attempts
    path('attempt/<uuid:attempt_id>/', views.take_test, name='take-test'),
    path('attempt/<uuid:attempt_id>/results/', views.test_results, name='test-results'),
    path('attempt/<uuid:attempt_id>/time-remaining/', views.get_time_remaining, name='time-remaining'),
    path('results/', views.results, name='results'),

    path('create/', views.create_test, name='create-test'),
    path('tests/<uuid:test_id>/upload-questions/', views.upload_questions, name='upload-questions'),
    path('test/<uuid:test_id>/', views.test_detail, name='test-detail'),
    # Add or update this URL pattern
    path('test/<uuid:test_id>/edit/', views.edit_test, name='edit-test'),
    path('test/<uuid:test_id>/toggle-status/', views.toggle_test_status, name='toggle-test-status'),
]