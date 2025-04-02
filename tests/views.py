from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseForbidden
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Test, Question, Choice, TestAttempt, Answer
from .serializers import (
    TestSerializer, 
    TestDetailSerializer, 
    TestAttemptSerializer,
    AnswerSerializer
)

# API Views
class TestListView(generics.ListAPIView):
    queryset = Test.objects.filter(is_active=True)
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]

class TestDetailView(generics.RetrieveAPIView):
    queryset = Test.objects.all()
    serializer_class = TestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

class StartTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, test_id):
        test = get_object_or_404(Test, pk=test_id, is_active=True)
        
        # Check if user already has an incomplete attempt
        existing_attempt = TestAttempt.objects.filter(
            user=request.user,
            test=test,
            is_completed=False
        ).first()
        
        if existing_attempt:
            serializer = TestAttemptSerializer(existing_attempt)
            return Response(serializer.data)
        
        # Create new test attempt
        test_attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            start_time=timezone.now()
        )
        
        serializer = TestAttemptSerializer(test_attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class SubmitAnswerView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, attempt_id):
        test_attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user)
        
        if test_attempt.is_completed:
            return Response({"error": "This test has already been completed"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AnswerSerializer(data=request.data)
        if serializer.is_valid():
            question_id = serializer.validated_data.get('question')
            question = get_object_or_404(Question, pk=question_id, test=test_attempt.test)
            
            # Check if answer already exists
            answer, created = Answer.objects.get_or_create(
                test_attempt=test_attempt,
                question=question,
                defaults={
                    'selected_choice': serializer.validated_data.get('selected_choice'),
                    'text_answer': serializer.validated_data.get('text_answer', ''),
                    'code_answer': serializer.validated_data.get('code_answer', '')
                }
            )
            
            if not created:
                answer.selected_choice = serializer.validated_data.get('selected_choice')
                answer.text_answer = serializer.validated_data.get('text_answer', '')
                answer.code_answer = serializer.validated_data.get('code_answer', '')
                answer.save()
            
            # Auto-evaluate MCQ answers
            answer.evaluate_answer()
            
            return Response(AnswerSerializer(answer).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubmitTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, attempt_id):
        test_attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user)
        
        if test_attempt.is_completed:
            return Response({"error": "This test has already been completed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark test as completed
        test_attempt.is_completed = True
        test_attempt.end_time = timezone.now()
        test_attempt.save()
        
        # Calculate score
        test_attempt.calculate_score()
        
        return Response(TestAttemptSerializer(test_attempt).data)

class TestAttemptListView(generics.ListAPIView):
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TestAttempt.objects.filter(user=self.request.user)

class TestAttemptDetailView(generics.RetrieveAPIView):
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TestAttempt.objects.filter(user=self.request.user)

# Frontend Views
@login_required
def home(request):
    return render(request, 'tests/home.html')

@login_required
def dashboard(request):
    test_attempts = TestAttempt.objects.filter(user=request.user)
    return render(request, 'tests/dashboard.html', {'test_attempts': test_attempts})

@login_required
def test_list(request):
    tests = Test.objects.filter(is_active=True)
    return render(request, 'tests/test_list.html', {'tests': tests})

@login_required
def test_detail(request, test_id):
    test = get_object_or_404(Test, pk=test_id, is_active=True)
    return render(request, 'tests/test_detail.html', {'test': test})

@login_required
def take_test(request, test_id):
    test = get_object_or_404(Test, pk=test_id, is_active=True)
    
    # Check if user already has an attempt
    test_attempt = TestAttempt.objects.filter(
        user=request.user,
        test=test,
        is_completed=False
    ).first()
    
    if not test_attempt:
        test_attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            start_time=timezone.now()
        )
    
    return render(request, 'tests/take_test.html', {
        'test': test,
        'test_attempt': test_attempt
    })

@login_required
def results(request):
    completed_attempts = TestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    )
    return render(request, 'tests/results.html', {'attempts': completed_attempts})

# Add these new frontend view functions

@login_required
def submit_test(request, attempt_id):
    test_attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user)
    
    if test_attempt.is_completed:
        messages.warning(request, "This test has already been submitted.")
        return redirect('frontend:attempt-detail', attempt_id=attempt_id)
    
    # Mark test as completed
    test_attempt.is_completed = True
    test_attempt.end_time = timezone.now()
    test_attempt.save()
    
    # Calculate score
    test_attempt.calculate_score()
    
    messages.success(request, "Your test has been submitted successfully.")
    return redirect('frontend:attempt-detail', attempt_id=attempt_id)

@login_required
def attempt_detail(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user)
    
    if not attempt.is_completed:
        messages.warning(request, "This test is still in progress.")
        return redirect('frontend:take-test', test_id=attempt.test.id)
    
    return render(request, 'tests/attempt_detail.html', {'attempt': attempt})
