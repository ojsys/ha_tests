from django.db import models
import uuid
import csv
import pandas as pd
from io import StringIO
from django.utils import timezone
from datetime import timedelta 
from users.models import User
from django.conf import settings

# Update the Test model to add duration_minutes field
class Test(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_limit = models.IntegerField(help_text="Time limit in minutes", default=60)
    duration_minutes = models.IntegerField(default=60)  # Add this field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    # In your Test model, make sure you have this method:
    def upload_questions_from_file(self, file):
        """
        Upload questions from CSV or Excel file
        """
        import pandas as pd
        from io import StringIO
        
        file_name = file.name.lower()
        if file_name.endswith('.csv'):
            # Process CSV file
            csv_data = file.read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_data))
        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            # Process Excel file
            df = pd.read_excel(file)
        else:
            raise ValueError("Unsupported file format. Please upload CSV or Excel file.")
        
        # Process each row
        question_count = 0
        for _, row in df.iterrows():
            # Get question type and points (with defaults)
            question_type = row.get('question_type', 'MCQ')
            points = row.get('points', 1)
            
            # Create question
            question = Question.objects.create(
                test=self,
                text=row['question_text'],
                question_type=question_type,
                points=points
            )
            
            # If MCQ, create options
            if question_type == 'MCQ':
                options = {
                    'A': row['option_a'],
                    'B': row['option_b'],
                    'C': row['option_c'],
                    'D': row['option_d']
                }
                
                for letter, text in options.items():
                    QuestionOption.objects.create(
                        question=question,
                        text=text,
                        is_correct=(letter == row['correct_answer'])
                    )
            
            question_count += 1
        
        return question_count

# Update the Question model to add missing fields
class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(
        max_length=10,
        choices=[
            ('MCQ', 'Multiple Choice'),
            ('TEXT', 'Text Answer'),
            ('CODE', 'Code Answer'),
        ],
        default='MCQ'
    )
    points = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.text[:50]

class QuestionOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.text} ({'Correct' if self.is_correct else 'Incorrect'})"



class TestAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.email} - {self.test.title}"
    
    def calculate_score(self):
        if not self.is_completed:
            return None
            
        # Fix: Use the related_name 'questions' instead of 'question_set'
        total_points = sum(q.points for q in self.test.questions.all())
        if total_points == 0:
            return 0
            
        earned_points = 0
        for answer in self.answer_set.all():
            if answer.is_correct:
                earned_points += answer.question.points
                
        score = (earned_points / total_points) * 100
        self.score = score
        self.save()
        return score
    
    def get_time_remaining(self):
        if self.is_completed:
            return 0
            
        elapsed = timezone.now() - self.start_time
        duration = timedelta(minutes=self.test.duration_minutes)
        remaining = duration - elapsed
        
        # Return seconds remaining or 0 if time is up
        return max(0, remaining.total_seconds())
    
    def is_time_up(self):
        return self.get_time_remaining() <= 0

class Answer(models.Model):
    test_attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Answer for {self.question.text[:30]}"
    
    def save(self, *args, **kwargs):
        # Determine if the answer is correct
        if self.question.question_type == 'MCQ' and self.selected_option:
            self.is_correct = self.selected_option.is_correct
        # For text/code questions, this would need manual grading
        super().save(*args, **kwargs)
