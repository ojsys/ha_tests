from django.db import models
from django.utils import timezone
from users.models import User

class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.IntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('CODE', 'Coding'),
        ('TEXT', 'Short Answer'),
    ]
    
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=4, choices=QUESTION_TYPES)
    points = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_question_type_display()} - {self.text[:50]}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.text

class TestAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.email} - {self.test.title}"
    
    def calculate_score(self):
        total_points = sum(q.points for q in self.test.questions.all())
        earned_points = 0
        
        for answer in self.answers.all():
            if answer.is_correct:
                earned_points += answer.question.points
        
        self.score = (earned_points / total_points) * 100 if total_points > 0 else 0
        self.save()
        return self.score

class Answer(models.Model):
    test_attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    code_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    admin_feedback = models.TextField(blank=True)
    
    def __str__(self):
        return f"Answer for {self.question}"
    
    def evaluate_answer(self):
        if self.question.question_type == 'MCQ':
            self.is_correct = self.selected_choice and self.selected_choice.is_correct
        elif self.question.question_type == 'CODE':
            # This would be connected to a code evaluation service
            # For now, we'll mark it as requiring manual review
            self.is_correct = None
        else:  # TEXT
            # Text answers require manual review
            self.is_correct = None
        
        self.save()
        return self.is_correct
