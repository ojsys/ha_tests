TEMPLATES = [
    {
        # ... existing settings ...
        'OPTIONS': {
            'context_processors': [
                # ... existing context processors ...
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'users.context_processors.site_settings',  # Add this line
            ],
        },
    },
]