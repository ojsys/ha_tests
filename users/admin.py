from django.contrib import admin
from .models import User, SiteSettings

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'application_status')
    list_filter = ('application_status',)
    search_fields = ('email', 'username', 'first_name', 'last_name')

class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow one instance
        if SiteSettings.objects.exists():
            return False
        return True

admin.site.register(User, UserAdmin)
admin.site.register(SiteSettings, SiteSettingsAdmin)
