from rest_framework import serializers
from .models import Test, Question, Choice, TestAttempt, Answer

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'points', 'choices']

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'duration_minutes', 'created_at']

class TestDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'duration_minutes', 'questions', 'created_at']

# Look for the AnswerSerializer class and ensure it's properly defined
class AnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    selected_choice = serializers.PrimaryKeyRelatedField(queryset=Choice.objects.all(), required=False, allow_null=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'question', 'selected_choice', 'text_answer', 'code_answer', 'is_correct']

class TestAttemptSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    test = TestSerializer(read_only=True)
    
    class Meta:
        model = TestAttempt
        fields = ['id', 'test', 'start_time', 'end_time', 'score', 'is_completed', 'answers']