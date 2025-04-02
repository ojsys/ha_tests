from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Test, Question, Choice, TestAttempt

User = get_user_model()

class TestFrontendViewsTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test
        self.test = Test.objects.create(
            title='Sample Test',
            description='A test for frontend testing',
            duration_minutes=30,
            is_active=True
        )
        
        # Create a question
        self.question = Question.objects.create(
            test=self.test,
            text='What is 2+2?',
            question_type='MCQ'
        )
        
        # Create choices
        self.choice1 = Choice.objects.create(
            question=self.question,
            text='3',
            is_correct=False
        )
        
        self.choice2 = Choice.objects.create(
            question=self.question,
            text='4',
            is_correct=True
        )
        
        # Setup client and force login (more reliable than client.login)
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_home_view(self):
        url = reverse('frontend:home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_view(self):
        url = reverse('frontend:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_test_list_view(self):
        url = reverse('frontend:test-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sample Test')
    
    def test_test_detail_view(self):
        url = reverse('frontend:test-detail', kwargs={'test_id': self.test.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sample Test')
    
    def test_take_test_view(self):
        url = reverse('frontend:take-test', kwargs={'test_id': self.test.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check if test attempt was created
        self.assertTrue(TestAttempt.objects.filter(user=self.user, test=self.test).exists())
    
    def test_submit_test_view(self):
        # First create a test attempt
        test_attempt = TestAttempt.objects.create(
            user=self.user,
            test=self.test,
            is_completed=False  # Make sure it's not completed
        )
        
        url = reverse('frontend:submit-test', kwargs={'attempt_id': test_attempt.id})
        response = self.client.post(url, follow=True)  # Use follow=True to follow redirects
        
        # Should redirect to attempt detail
        self.assertEqual(response.status_code, 200)
        
        # Refresh from database to get updated values
        test_attempt.refresh_from_db()
        self.assertTrue(test_attempt.is_completed)