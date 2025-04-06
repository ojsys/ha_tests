import base64
import os
import uuid
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Test, Question, QuestionOption
from .forms import TestForm, QuestionUploadForm
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Test, Question, QuestionOption, TestAttempt, Answer, TestCapture
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
    """Dashboard view showing user's test statistics and recent attempts"""
    # Get all active tests
    available_tests = Test.objects.filter(is_active=True).count()
    
    # Get user's completed test attempts
    completed_attempts = TestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    )
    
    completed_tests = completed_attempts.count()
    
    # Calculate average score
    average_score = 0
    if completed_tests > 0:
        total_score = sum(attempt.score or 0 for attempt in completed_attempts)
        average_score = total_score / completed_tests
    
    # Get recent test attempts (limit to 5)
    test_attempts = TestAttempt.objects.filter(
        user=request.user
    ).order_by('-start_time')[:5]
    
    context = {
        'available_tests': available_tests,
        'completed_tests': completed_tests,
        'average_score': average_score,
        'test_attempts': test_attempts,
    }
    
    return render(request, 'tests/dashboard.html', context)

@login_required
def test_list(request):
    tests = Test.objects.filter(is_active=True)
    return render(request, 'tests/test_list.html', {'tests': tests})

@login_required
def test_detail(request, test_id):
    test = get_object_or_404(Test, pk=test_id, is_active=True)
    return render(request, 'tests/test_detail.html', {'test': test})

@login_required
def take_test(request, attempt_id):
    test_attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    test = test_attempt.test
    
    # Check if test is already completed
    if test_attempt.is_completed:
        return redirect('tests:test-results', attempt_id=test_attempt.id)
    
    # Check if time is up
    if test_attempt.is_time_up():
        test_attempt.is_completed = True
        test_attempt.end_time = timezone.now()
        test_attempt.save()
        test_attempt.calculate_score()
        return redirect('tests:test-results', attempt_id=test_attempt.id)
    
    # Get all questions for this test
    questions = test.questions.all()
    
    # Get existing answers
    answers = Answer.objects.filter(test_attempt=test_attempt)
    answered_question_ids = [answer.question_id for answer in answers]
    
    # Create dictionaries to store selected choices and text answers
    selected_choices = {}
    text_answers = {}
    
    for answer in answers:
        if answer.question.question_type == 'MCQ':
            if answer.selected_option:  # Changed from selected_choice to selected_option
                selected_choices[answer.question.id] = answer.selected_option.id
        else:
            text_answers[answer.question.id] = answer.text_answer
    
    # Process form submission
    if request.method == 'POST':
        for question in questions:
            if question.question_type == 'MCQ':
                option_id = request.POST.get(f'question_{question.id}')
                if option_id:
                    selected_option = get_object_or_404(QuestionOption, id=option_id)
                    
                    # Update or create answer - using selected_option instead of selected_choice
                    answer, created = Answer.objects.update_or_create(
                        test_attempt=test_attempt,
                        question=question,
                        defaults={
                            'selected_option': selected_option,  # This is the correct field name
                            'text_answer': None
                        }
                    )
            else:  # TEXT or CODE
                text_answer = request.POST.get(f'question_{question.id}')
                if text_answer:
                    # Update or create answer
                    answer, created = Answer.objects.update_or_create(
                        test_attempt=test_attempt,
                        question=question,
                        defaults={
                            'selected_option': None,  # This is the correct field name
                            'text_answer': text_answer
                        }
                    )
        
        # Check if user is submitting the test
        if 'submit_test' in request.POST:
            test_attempt.is_completed = True
            test_attempt.end_time = timezone.now()
            test_attempt.save()
            test_attempt.calculate_score()
            return redirect('tests:test-results', attempt_id=test_attempt.id)
        
        # If just saving, redirect back to the test
        messages.success(request, "Your answers have been saved.")
        return redirect('tests:take-test', attempt_id=test_attempt.id)
    
    # Create a dictionary to store options for each question
    question_options = {}
    for question in questions:
        if question.question_type == 'MCQ':
            # Get options directly from the QuestionOption model
            options = QuestionOption.objects.filter(question=question)
            question_options[question.id] = options
    
    context = {
        'test': test,
        'attempt': test_attempt,  # Changed from test_attempt to attempt to match template
        'questions': questions,
        'question_options': question_options,
        'selected_choices': selected_choices,
        'text_answers': text_answers,
        'time_remaining': test_attempt.get_time_remaining(),
        'answers': answered_question_ids,  # Added this to match template's expectation
    }
    
    return render(request, 'tests/take_test.html', context)

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

@login_required
def create_test(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save()
            messages.success(request, f"Test '{test.title}' created successfully.")
            return redirect('tests:upload-questions', test_id=test.id)
    else:
        form = TestForm()
    
    return render(request, 'tests/create_test.html', {'form': form})



@staff_member_required
def upload_questions(request, test_id):
    """View for superusers to upload questions via CSV/Excel file"""
    test = get_object_or_404(Test, id=test_id)
    
    if request.method == 'POST':
        form = QuestionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file']
                question_count = test.upload_questions_from_file(file)
                messages.success(request, f"Successfully uploaded {question_count} questions.")
                return redirect('tests:test-detail', test_id=test.id)
            except Exception as e:
                messages.error(request, f"Error uploading questions: {str(e)}")
    else:
        form = QuestionUploadForm()
    
    return render(request, 'tests/upload_questions.html', {
        'form': form,
        'test': test
    })

@login_required
def test_detail(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    
    # Get all user's attempts for this test
    user_attempts = TestAttempt.objects.filter(
        user=request.user,
        test=test
    ).order_by('-start_time')
    
    # Count completed attempts
    user_completed_attempts = user_attempts.filter(is_completed=True).count()
    
    # Get the latest attempt (completed or not)
    user_attempt = user_attempts.first() if user_attempts.exists() else None
    
    # Get the latest completed attempt
    user_latest_attempt = user_attempts.filter(is_completed=True).first()
    
    # Check if user has completed the test
    user_completed_test = user_attempt and user_attempt.is_completed
    
    # Count question types
    mcq_count = test.questions.filter(question_type='MCQ').count()
    text_count = test.questions.filter(question_type='TEXT').count()
    code_count = test.questions.filter(question_type='CODE').count()
    
    # Calculate total points
    total_points = test.questions.count()
    
    context = {
        'test': test,
        'user_attempt': user_attempt,
        'user_latest_attempt': user_latest_attempt or user_attempt,
        'user_completed_test': user_completed_test,
        'user_completed_attempts': user_completed_attempts,
        'mcq_count': mcq_count,
        'text_count': text_count,
        'code_count': code_count,
        'total_points': total_points,
    }
    
    return render(request, 'tests/test_detail.html', context)

# Add this view to handle test editing
@staff_member_required
def edit_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    
    if request.method == 'POST':
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, "Test updated successfully.")
            return redirect('tests:test-detail', test_id=test.id)
    else:
        form = TestForm(instance=test)
    
    return render(request, 'tests/edit_test.html', {
        'form': form,
        'test': test
    })

# Add this view to toggle test status
@staff_member_required
def toggle_test_status(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    test.is_active = not test.is_active
    test.save()
    
    status = "activated" if test.is_active else "deactivated"
    messages.success(request, f"Test {status} successfully.")
    
    return redirect('tests:test-detail', test_id=test.id)



# Add this new view function
def test_consent(request, attempt_id):
    """
    Display a consent page before starting the test, warning about image capture
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Check if the attempt belongs to the current user
    if attempt.user != request.user:
        messages.error(request, "You don't have permission to access this test attempt.")
        return redirect('tests:dashboard')
    
    # If the user has already consented, redirect to the test
    if request.method == 'POST':
        # Mark that the user has consented
        attempt.has_consented = True
        attempt.save()
        return redirect('tests:take-test', attempt_id=attempt_id)
    
    return render(request, 'tests/test_consent.html', {
        'attempt': attempt,
        'test': attempt.test
    })

# Modify your start_test view to redirect to the consent page instead of directly to take_test
def start_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    
    # Check if test is active
    if not test.is_active:
        messages.error(request, "This test is not currently active.")
        return redirect('tests:test-detail', test_id=test.id)
    
    # Count completed attempts
    completed_attempts = TestAttempt.objects.filter(
        user=request.user,
        test=test,
        is_completed=True
    ).count()
    
    # Check if user has already attempted the test twice
    if completed_attempts >= 2:
        messages.info(request, "You have already attempted this test twice.")
        return redirect('tests:test-detail', test_id=test.id)
    
    # Check if user has an incomplete attempt
    existing_attempt = TestAttempt.objects.filter(
        user=request.user,
        test=test,
        is_completed=False
    ).first()
    
    if existing_attempt:
        return redirect('tests:take-test', attempt_id=existing_attempt.id)
    
    # Create a new test attempt
    test_attempt = TestAttempt.objects.create(
        user=request.user,
        test=test,
        start_time=timezone.now(),
        end_time=None,
        is_completed=False,
        score=0
    )
    
    return redirect('tests:take-test', attempt_id=test_attempt.id)

@login_required
def take_test(request, attempt_id):
    test_attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    test = test_attempt.test
    
    # Check if test is already completed
    if test_attempt.is_completed:
        return redirect('tests:test-results', attempt_id=test_attempt.id)
    
    # Check if time is up
    if test_attempt.is_time_up():
        test_attempt.is_completed = True
        test_attempt.end_time = timezone.now()
        test_attempt.save()
        test_attempt.calculate_score()
        return redirect('tests:test-results', attempt_id=test_attempt.id)
    
    # Get all questions for this test
    questions = test.questions.all()
    
    # Get existing answers
    answers = Answer.objects.filter(test_attempt=test_attempt)
    answered_question_ids = [answer.question_id for answer in answers]
    
    # Create dictionaries to store selected choices and text answers
    selected_choices = {}
    text_answers = {}
    
    for answer in answers:
        if answer.question.question_type == 'MCQ':
            if answer.selected_option:  # Changed from selected_choice to selected_option
                selected_choices[answer.question.id] = answer.selected_option.id
        else:
            text_answers[answer.question.id] = answer.text_answer
    
    # Process form submission
    if request.method == 'POST':
        for question in questions:
            if question.question_type == 'MCQ':
                option_id = request.POST.get(f'question_{question.id}')
                if option_id:
                    selected_option = get_object_or_404(QuestionOption, id=option_id)
                    
                    # Update or create answer - using selected_option instead of selected_choice
                    answer, created = Answer.objects.update_or_create(
                        test_attempt=test_attempt,
                        question=question,
                        defaults={
                            'selected_option': selected_option,  # This is the correct field name
                            'text_answer': None
                        }
                    )
            else:  # TEXT or CODE
                text_answer = request.POST.get(f'question_{question.id}')
                if text_answer:
                    # Update or create answer
                    answer, created = Answer.objects.update_or_create(
                        test_attempt=test_attempt,
                        question=question,
                        defaults={
                            'selected_option': None,  # This is the correct field name
                            'text_answer': text_answer
                        }
                    )
        
        # Check if user is submitting the test
        if 'submit_test' in request.POST:
            test_attempt.is_completed = True
            test_attempt.end_time = timezone.now()
            test_attempt.save()
            test_attempt.calculate_score()
            return redirect('tests:test-results', attempt_id=test_attempt.id)
        
        # If just saving, redirect back to the test
        messages.success(request, "Your answers have been saved.")
        return redirect('tests:take-test', attempt_id=test_attempt.id)
    
    # Create a dictionary to store options for each question
    question_options = {}
    for question in questions:
        if question.question_type == 'MCQ':
            # Get options directly from the QuestionOption model
            options = QuestionOption.objects.filter(question=question)
            question_options[question.id] = options
    
    context = {
        'test': test,
        'attempt': test_attempt,
        'questions': questions,
        'question_options': question_options,
        'selected_choices': selected_choices,
        'text_answers': text_answers,
        'time_remaining': test_attempt.get_time_remaining(),
        'answered_question_ids': answered_question_ids,
    }
    
    return render(request, 'tests/take_test.html', context)

@login_required
def test_results(request, attempt_id):
    test_attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Calculate score if not already calculated
    if test_attempt.score is None and test_attempt.is_completed:
        test_attempt.calculate_score()
    
    # Get all answers for this attempt
    answers = Answer.objects.filter(test_attempt=test_attempt).select_related('question', 'selected_option')
    
    context = {
        'test_attempt': test_attempt,
        'test': test_attempt.test,
        'answers': answers
    }
    
    return render(request, 'tests/test_results.html', context)

# Add this new view function
def time_remaining(request, attempt_id):
    """Return the time remaining for a test attempt as JSON"""
    try:
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
        
        # Check if test is already completed
        if attempt.is_completed:
            return JsonResponse({
                'is_completed': True,
                'time_remaining': 0
            })
        
        # Get time remaining in seconds
        time_remaining = attempt.get_time_remaining()
        
        return JsonResponse({
            'is_completed': False,
            'time_remaining': time_remaining
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

@login_required
def get_time_remaining(request, attempt_id):
    """AJAX endpoint to get remaining time for a test attempt"""
    test_attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    return JsonResponse({
        'time_remaining': test_attempt.get_time_remaining(),
        'is_completed': test_attempt.is_completed
    })


@login_required
def attempt_list(request):
    """View all test attempts by the current user"""
    test_attempts = TestAttempt.objects.filter(
        user=request.user
    ).order_by('-start_time')
    
    context = {
        'test_attempts': test_attempts,
    }
    
    return render(request, 'tests/attempt_list.html', context)



@require_POST
@csrf_exempt
def capture_image(request, attempt_id):
    """Handle image captures from test monitoring"""
    try:
        attempt = TestAttempt.objects.get(id=attempt_id)
        
        if 'image' in request.FILES:
            image = request.FILES['image']
            
            # Create the capture
            capture = TestCapture.objects.create(
                attempt=attempt,
                image=image
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Image captured successfully',
                'capture_id': str(capture.id)
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No image provided'
            }, status=400)
            
    except TestAttempt.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Test attempt with ID {attempt_id} not found'
        }, status=404)
    except Exception as e:
        import traceback
        print(f"Error in capture_image: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def get_captures(request, attempt_id):
    """
    Get all captures for a test attempt (for admin/review purposes)
    """
    # Check if user is staff/admin
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    try:
        attempt = TestAttempt.objects.get(id=attempt_id)
        captures = TestCapture.objects.filter(attempt=attempt).order_by('timestamp')
        
        captures_data = [
            {
                'id': capture.id,
                'image_url': capture.image.url,
                'timestamp': capture.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for capture in captures
        ]
        
        return JsonResponse({'status': 'success', 'captures': captures_data})
    
    except TestAttempt.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Test attempt not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Add this to your existing views.py file

@staff_member_required
def admin_view_captures(request, attempt_id):
    """Admin view to see all captures for a specific test attempt"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    captures = TestCapture.objects.filter(attempt=attempt).order_by('-timestamp')
    
    return render(request, 'admin/tests/test_captures.html', {
        'attempt': attempt,
        'captures': captures,
        'title': f'Captures for {attempt.user.username} - {attempt.test.title}'
    })

@login_required
def user_test_captures(request, attempt_id):
    """View for users to see their own captures from a test attempt"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    captures = TestCapture.objects.filter(attempt=attempt).order_by('-timestamp')
    
    return render(request, 'tests/user_test_captures.html', {
        'attempt': attempt,
        'captures': captures,
        'title': f'Your Images from {attempt.test.title}'
    })
