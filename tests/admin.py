from django.contrib import admin
from .models import Test, Question, Choice, TestAttempt, Answer

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question_type', 'test', 'points')
    list_filter = ('question_type', 'test')
    search_fields = ('text',)
    inlines = [ChoiceInline]

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    inlines = [QuestionInline]

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ('question', 'selected_choice', 'text_answer', 'code_answer')

class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'start_time', 'end_time', 'score', 'is_completed')
    list_filter = ('is_completed', 'test')
    search_fields = ('user__email', 'test__title')
    inlines = [AnswerInline]

admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(TestAttempt, TestAttemptAdmin)
admin.site.register(Answer)
