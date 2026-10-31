
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
     'DEFAULT_THROTTLE_RATES': {
        'register': '10/hour',
        'login': '20/hour',
        'password_reset_request': '5/hour',
        'password_reset_confirm': '10/hour',
    },
}
