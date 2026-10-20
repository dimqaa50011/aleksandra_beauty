"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from .sitemaps import (
    StaticViewSitemap,
    CategorySitemap,
    ServiceSitemap,
    BlogPostSitemap,
)

sitemaps = {
    'static':     StaticViewSitemap,
    'categories': CategorySitemap,
    'services':   ServiceSitemap,
    'blog':       BlogPostSitemap,
}


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('booking_app.urls')),
    path('', include("beauty_app.urls")),
    path('privacy/', TemplateView.as_view(template_name='privacy_policy.html'), name='privacy_policy'),
    path('posts/', include("gen_posts_app.urls")),
    # Сертификаты (встраиваются в админку, доступ только у админов)
    path('admin-dashboard/certificates/', include('cert_app.urls')),
    path('robots.txt',
         TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
         name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)