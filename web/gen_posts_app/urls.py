from django.urls import path
from . import views
from .apps import GenPostsAppConfig

app_name = GenPostsAppConfig.name

urlpatterns = [
    path('posts/', views.gen_posts, name='gen_posts'),
    path('posts/<int:idea_id>/generate/', views.generate_post, name='generate_post'),
    path('posts/<int:idea_id>/', views.gen_posts, name='idea_posts'),  # Новая строка
]