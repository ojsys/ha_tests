from .models import SiteSettings

def site_settings(request):
    """
    Add site settings to the context of all templates
    """
    try:
        settings = SiteSettings.objects.first()
    except:
        settings = None
    
    return {
        'site_settings': settings
    }