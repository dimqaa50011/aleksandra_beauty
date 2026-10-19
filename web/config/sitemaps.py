from django.contrib.sitemaps import Sitemap
from django.urls import reverse

# Импорты — из разных приложений, это нормально
from beauty_app.models import ServiceCategory, Service
from gen_posts_app.models import PostContent


class StaticViewSitemap(Sitemap):
    """Главная, блог (список), форма записи."""
    protocol = 'https'

    def items(self):
        return [
            # (имя URL, priority, changefreq)
            ('beauty_app:landing',                  1.0, 'weekly'),
            ('gen_posts_app:blog_list',             0.8, 'weekly'),
            ('booking_app:booking_create',          0.8, 'monthly'),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class CategorySitemap(Sitemap):
    """beauty_app: /services/<int:category_id>/"""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return ServiceCategory.objects.all()

    def location(self, obj):
        return reverse('beauty_app:category_services', args=[obj.pk])

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)


class ServiceSitemap(Sitemap):
    """beauty_app: /service/<int:service_id>/"""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Service.objects.all()

    def location(self, obj):
        return reverse('beauty_app:service_detail', args=[obj.pk])

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)


class BlogPostSitemap(Sitemap):
    """gen_posts_app: /posts/blog/<int:post_id>/ — только is_published=True"""
    protocol = 'https'
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return PostContent.objects.filter(is_published=True).order_by('-updated_at')

    def location(self, obj):
        return reverse('gen_posts_app:blog_post_detail', args=[obj.pk])

    def lastmod(self, obj):
        return obj.updated_at