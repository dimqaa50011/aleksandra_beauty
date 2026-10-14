from .models import FAQ

def faq_context(request):
    """Добавляет список FAQ во все шаблоны"""
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'created_at')
    return {'faqs': faqs}