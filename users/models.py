from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from allauth.account.signals import email_confirmed

class User(AbstractUser):
    email = models.EmailField(unique=True)
    # Add middle_name field
    middle_name = models.CharField(max_length=150, blank=True)
    lga = models.CharField(max_length=100, blank=True)
    application_status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
        ],
        default='Pending'
    )
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
# Add to the existing models.py file
class SiteSettings(models.Model):
    site_title = models.CharField(max_length=100, default="AfricaPlan Foundation")
    site_description = models.TextField(default="Empowering African youth through education and technology")
    hero_title = models.CharField(max_length=200, default="Welcome to AfricaPlan Foundation Test Platform")
    hero_subtitle = models.TextField(default="Take assessments and improve your skills")
    hero_image = models.ImageField(upload_to='hero_images/', null=True, blank=True)
    primary_color = models.CharField(max_length=20, default="#006400")
    secondary_color = models.CharField(max_length=20, default="#00008B")
    accent_color = models.CharField(max_length=20, default="#FFD700")
    logo = models.ImageField(upload_to='logos/', null=True, blank=True, help_text="Site logo")
        
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return self.site_title
     
    def save(self, *args, **kwargs):
    # Ensure only one instance exists
        if SiteSettings.objects.exists() and not self.pk:
            raise ValidationError("There can only be one SiteSettings instance")
        return super().save(*args, **kwargs)

# Add a signal receiver to update application status when email is confirmed
@receiver(email_confirmed)
def update_user_application_status(sender, request, email_address, **kwargs):
    """
    When a user confirms their email, automatically set their application status to 'Approved'
    """
    # Get the user associated with this email address
    user = email_address.user
    
    # Update the application status to 'Approved'
    if user.application_status == 'Pending':
        user.application_status = 'Approved'
        user.save()
