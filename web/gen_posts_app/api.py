from .models import BlogArticle
from django.utils.text import slugify
import random
import string

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated



from .models import PostIdea
from django_q.tasks import async_task
from django.shortcuts import get_object_or_404

class AdminPostIdeasAPIView(APIView):
    """
    GET: Список идей
    POST: Создать новую идею
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ideas = PostIdea.objects.all().order_by('-created_at')
        data = []
        for idea in ideas:
            data.append({
                'id': idea.id,
                'topic': idea.topic,
                'description': idea.description,
                'status': idea.status,
                'status_display': idea.get_status_display(),
                'platform': idea.get_platform_display(),
                'posts_count': idea.get_posts_count(),
                'created_at': idea.created_at.strftime('%d.%m.%Y'),
            })
        return Response({'ideas': data}, status=status.HTTP_200_OK)

    def post(self, request):
        topic = request.data.get('topic', '').strip()
        description = request.data.get('description', '').strip()
        platform = request.data.get('platform', 'telegram')

        if not topic:
            return Response({'error': 'Тема поста обязательна'}, status=status.HTTP_400_BAD_REQUEST)

        idea = PostIdea.objects.create(
            topic=topic, 
            description=description, 
            platform=platform
        )
        return Response({'success': True, 'id': idea.id}, status=status.HTTP_201_CREATED)


class AdminGeneratePostAPIView(APIView):
    """
    POST: Запустить генерацию поста
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, idea_id):
        idea = get_object_or_404(PostIdea, id=idea_id)
        
        # Запускаем вашу фоновую задачу (проверьте путь к функции tasks)
        async_task('gen_posts_app.tasks.generate_post_task', idea.id)
        
        return Response({'success': True, 'message': 'Генерация запущена в фоне'}, status=status.HTTP_200_OK)


class AdminBlogArticlesAPIView(APIView):
    """
    GET: Список статей блога
    POST: Создать новую статью
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        articles = BlogArticle.objects.all().order_by('-created_at')
        data = []
        for a in articles:
            data.append({
                'id': a.id,
                'title': a.title,
                'slug': a.slug,
                'is_published': a.is_published,
                'views_count': a.views_count,
                'created_at': a.created_at.strftime('%d.%m.%Y'),
            })
        return Response({'articles': data}, status=status.HTTP_200_OK)

    def post(self, request):
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        excerpt = request.data.get('excerpt', '').strip()
        seo_description = request.data.get('seo_description', '').strip()
        
        if not title or not content:
            return Response({'error': 'Заголовок и текст обязательны'}, status=status.HTTP_400_BAD_REQUEST)

        # Генерируем уникальный slug
        base_slug = slugify(title, allow_unicode=True)
        slug = base_slug
        while BlogArticle.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{random.randint(100, 999)}"

        article = BlogArticle.objects.create(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            seo_description=seo_description,
            is_published=True # По умолчанию публикуем сразу
        )
        
        return Response({'success': True, 'id': article.id}, status=status.HTTP_201_CREATED)