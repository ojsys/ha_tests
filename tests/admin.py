from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from .models import Test, Question, QuestionOption, TestAttempt, Answer, TestCapture
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

class TestCaptureInline(admin.TabularInline):
    model = TestCapture
    readonly_fields = ['timestamp', 'image_preview']
    fields = ['timestamp', 'image_preview']
    extra = 0
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    
    image_preview.short_description = 'Image Preview'

@admin.register(TestCapture)
class TestCaptureAdmin(admin.ModelAdmin):
    list_display = ['id', 'attempt', 'timestamp', 'image_preview']
    list_filter = ['timestamp', 'attempt__user']
    search_fields = ['attempt__user__username', 'attempt__user__email']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="auto" />', obj.image.url)
        return "No Image"
    
    image_preview.short_description = 'Image Preview'

# Merge the two TestAttemptAdmin classes
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_full_name', 'get_phone_number', 'test', 'start_time', 'end_time', 'is_completed', 
                    'score', 'get_duration', 'get_attempt_number', 'capture_count', 'first_image_preview')
    list_filter = ('is_completed', 'test', 'start_time')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'test__title', 'user__email')
    readonly_fields = ['start_time', 'score', 'capture_count', 'all_captures_preview']
    actions = ['export_to_excel']
    inlines = [TestCaptureInline]
    
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('<path:object_id>/captures/', 
                 self.admin_site.admin_view(self.view_captures), 
                 name='tests_testattempt_captures'),
        ]
        return my_urls + urls
    
    def view_captures(self, request, object_id):
        attempt = get_object_or_404(TestAttempt, pk=object_id)
        captures = TestCapture.objects.filter(attempt=attempt).order_by('-timestamp')
        
        context = {
            'title': f'Captures for {attempt.user.username} - {attempt.test.title}',
            'attempt': attempt,
            'captures': captures,
            'opts': self.model._meta,
            'original': attempt,
            'media': self.media,
        }
        return TemplateResponse(request, 'admin/tests/test_captures.html', context)
    
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
    
    def capture_count(self, obj):
        count = obj.captures.count()
        if count > 0:
            return format_html('<a href="{}">{} captures</a>', 
                              f'../tests/testattempt/{obj.id}/captures/', count)
        return count
    
    capture_count.short_description = 'Captures'
    
    def first_image_preview(self, obj):
        first_capture = obj.captures.order_by('timestamp').first()
        if first_capture and first_capture.image:
            return format_html('<a href="{}"><img src="{}" width="100" height="auto" /></a>', 
                              f'../tests/testattempt/{obj.id}/captures/', 
                              first_capture.image.url)
        return "No captures"
    
    first_image_preview.short_description = 'First Capture'
    
    def all_captures_preview(self, obj):
        captures = obj.captures.all()
        if not captures:
            return "No captures available"
        
        html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
        for capture in captures:
            if capture.image:
                html += f'<div style="margin: 5px;"><img src="{capture.image.url}" width="150" height="auto" />'
                html += f'<p style="text-align: center; font-size: 0.8em;">{capture.timestamp}</p></div>'
        html += '</div>'
        
        return format_html(html)
    
    all_captures_preview.short_description = 'All Captures'
    
    def export_to_excel(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=test_attempts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Phone Number', 'Test', 'Start Time', 'End Time', 
            'Completed', 'Score', 'Duration', 'Attempt #', 'Captures'
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
                self.get_attempt_number(obj),
                obj.captures.count()
            ])
        
        return response
    export_to_excel.short_description = "Export selected attempts to Excel"

# Register the models
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(TestAttempt, TestAttemptAdmin)
admin.site.register(Answer)
