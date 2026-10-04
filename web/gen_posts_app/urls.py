from django.urls import path
from . import views
from .apps import GenPostsAppConfig

app_name = GenPostsAppConfig.name

urlpatterns = [
    path('posts/', views.gen_posts, name='gen_posts'),
    path('posts/<int:idea_id>/generate/', views.generate_post, name='generate_post'),
    path('posts/<int:idea_id>/', views.idea_posts, name='idea_posts'),  # Новая строка
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<int:post_id>/', views.blog_post_detail, name='blog_post_detail'),
    path('posts/<int:idea_id>/<int:post_id>/status/', 
         views.UpdatePostStatusView.as_view(), 
         name='update_post_status'),
]