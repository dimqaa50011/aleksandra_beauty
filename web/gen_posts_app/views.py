from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django_q.tasks import async_task
from .models import PostIdea, PostContent

def gen_posts(request):
    """Главная страница управления идеями постов (список и добавление)"""
    if request.method == 'POST' and 'add_idea' in request.POST:
        topic = request.POST.get('topic', '').strip()
        description = request.POST.get('description', '').strip()
        platform = request.POST.get('platform', 'telegram')
        
        if topic:
            PostIdea.objects.create(
                topic=topic,
                description=description,
                platform=platform
            )
            messages.success(request, f'✅ Идея "{topic}" добавлена!')
        else:
            messages.error(request, '❌ Тема поста обязательна для заполнения.')
        
        return redirect('gen_posts_app:gen_posts')
    
    ideas = PostIdea.objects.all()
    return render(request, 'gen_posts_app/gen_posts.html', {'ideas': ideas})


def generate_post(request, idea_id):
    """Отдельная вьюха для запуска генерации в фоне"""
    idea = get_object_or_404(PostIdea, id=idea_id)
    
    if request.method == 'POST':
        async_task('gen_posts_app.tasks.generate_post_task', idea.id)
        messages.success(request, f'⏳ Генерация для "{idea.topic}" запущена в фоне!')
    
    # Перенаправляем сразу на страницу просмотра постов этой идеи
    return redirect('gen_posts_app:idea_posts', idea_id=idea.id)


def idea_posts(request, idea_id):
    """Страница со всеми сгенерированными постами для конкретной идеи"""
    idea = get_object_or_404(PostIdea, id=idea_id)
    
    # Получаем посты, отсортированные по дате создания (сначала самые новые)
    posts = idea.posts.all().order_by('-created_at')
    
    context = {
        'idea': idea,
        'posts': posts,
    }
    
    return render(request, 'gen_posts_app/idea_posts.html', context)