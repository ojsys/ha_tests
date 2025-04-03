from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import get_object_or_404
from .models import Test, Question, QuestionOption, TestAttempt, Answer
from .forms import QuestionUploadForm
import csv
from datetime import datetime

class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question_type', 'test', 'points')
    list_filter = ('question_type', 'test')
    search_fields = ('text',)
    inlines = [QuestionOptionInline]

class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    inlines = [QuestionInline]
    
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('<path:object_id>/upload-questions/', 
                 self.admin_site.admin_view(self.upload_questions), 
                 name='tests_test_upload_questions'),
        ]
        return my_urls + urls
    
    def upload_questions(self, request, object_id):
        test = get_object_or_404(Test, pk=object_id)
        
        if request.method == 'POST':
            form = QuestionUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    file = request.FILES['file']
                    count = test.upload_questions_from_file(file)
                    self.message_user(request, f"Successfully uploaded {count} questions.")
                    return HttpResponseRedirect("../")
                except Exception as e:
                    self.message_user(request, f"Error: {str(e)}", level='error')
        else:
            form = QuestionUploadForm()
        
        context = {
            'title': f'Upload Questions for {test.title}',
            'form': form,
            'opts': self.model._meta,
            'original': test,
            'media': self.media,
        }
        return TemplateResponse(request, 'admin/tests/upload_form.html', context)



class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_full_name', 'get_phone_number', 'test', 'start_time', 'end_time', 'is_completed', 
                    'score', 'get_duration', 'get_attempt_number')
    list_filter = ('is_completed', 'test')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'test__title')
    actions = ['export_to_excel']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'User'
    
    def get_phone_number(self, obj):
        # Try to get phone number from Profile model
        try:
            return obj.user.phone_number or "N/A"
        except:
            return "N/A"
    get_phone_number.short_description = 'Phone'
    
    def get_duration(self, obj):
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            minutes, seconds = divmod(duration.total_seconds(), 60)
            return f"{int(minutes)}m {int(seconds)}s"
        return "In progress"
    get_duration.short_description = 'Duration'
    
    def get_attempt_number(self, obj):
        # Count this user's attempts for this test
        attempt_number = TestAttempt.objects.filter(
            user=obj.user,
            test=obj.test,
            start_time__lte=obj.start_time
        ).count()
        return attempt_number
    get_attempt_number.short_description = 'Attempt #'
    
    def export_to_excel(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=test_attempts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Phone Number', 'Test', 'Start Time', 'End Time', 
            'Completed', 'Score', 'Duration', 'Attempt #'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.user.get_full_name() or obj.user.username,
                self.get_phone_number(obj),
                obj.test.title,
                obj.start_time,
                obj.end_time,
                'Yes' if obj.is_completed else 'No',
                obj.score,
                self.get_duration(obj),
                self.get_attempt_number(obj)
            ])
        
        return response
    export_to_excel.short_description = "Export selected attempts to Excel"

admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(QuestionOption)
admin.site.register(TestAttempt, TestAttemptAdmin)
admin.site.register(Answer)
