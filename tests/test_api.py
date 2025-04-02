from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Test, Question, Choice, TestAttempt, Answer

User = get_user_model()

class TestAPITestCase(TestCase):
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
            description='A test for API testing',
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
        
        self.choice3 = Choice.objects.create(
            question=self.question,
            text='5',
            is_correct=False
        )
        
        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_test_list_api(self):
        url = reverse('api:test-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_test_detail_api(self):
        url = reverse('api:test-detail', kwargs={'pk': self.test.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Sample Test')
    
    def test_start_test_api(self):
        url = reverse('api:start-test', kwargs={'test_id': self.test.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if test attempt was created
        self.assertTrue(TestAttempt.objects.filter(user=self.user, test=self.test).exists())
    
    def test_submit_answer_api(self):
        # First create a test attempt
        test_attempt = TestAttempt.objects.create(
            user=self.user,
            test=self.test
        )
        
        url = reverse('api:submit-answer', kwargs={'attempt_id': test_attempt.id})
        
        # Let's inspect what's happening with the data
        question_id = self.question.id
        choice_id = self.choice2.id
        
        # Create a simple dictionary with primitive values
        data = {
            'question': question_id,
            'selected_choice': choice_id
        }
        
        # Try a different approach with the client
        from django.test.client import encode_multipart
        content = encode_multipart('boundary', data)
        
        response = self.client.post(
            url,
            content,
            content_type='multipart/form-data; boundary=boundary'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if answer was created and evaluated correctly
        answer = Answer.objects.get(test_attempt=test_attempt, question=self.question)
        self.assertEqual(answer.selected_choice, self.choice2)
        self.assertTrue(answer.is_correct)
    
    def test_submit_test_api(self):
        # First create a test attempt
        test_attempt = TestAttempt.objects.create(
            user=self.user,
            test=self.test
        )
        
        url = reverse('api:submit-test', kwargs={'attempt_id': test_attempt.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if test was marked as completed
        test_attempt.refresh_from_db()
        self.assertTrue(test_attempt.is_completed)