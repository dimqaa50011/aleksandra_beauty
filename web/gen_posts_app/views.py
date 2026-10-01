from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import PostIdea, PostContent

def gen_posts(request):
    """Главная страница управления идеями постов (только список и добавление)"""
    
    # Обработка формы добавления новой идеи
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
    
    # Получаем все идеи
    ideas = PostIdea.objects.all()
    
    context = {
        'ideas': ideas,
    }
    
    return render(request, 'gen_posts_app/gen_posts.html', context)


def generate_post(request, idea_id):
    """Отдельная вьюха для генерации поста (пока заглушка)"""
    
    idea = get_object_or_404(PostIdea, id=idea_id)
    
    if request.method == 'POST':
        # TODO: Здесь будет вызов GigaChat API
        # Пока создаём заглушку
        PostContent.objects.create(
            idea=idea,
            variant_name='Вариант 1',
            headline=f'Заголовок для: {idea.topic}',
            body=f'Текст поста про {idea.topic}. Здесь будет сгенерированный текст от GigaChat.',
            hashtags='#sashasugar #spb #beauty'
        )
        
        # Меняем статус идеи
        idea.status = 'in_progress'
        idea.save()
        
        messages.success(request, f'✨ Пост для идеи "{idea.topic}" сгенерирован!')
    
    return redirect('gen_posts_app:gen_posts')

def idea_posts(request, idea_id):
    """Страница со всеми сгенерированными постами для конкретной идеи"""
    
    idea = get_object_or_404(PostIdea, id=idea_id)
    posts = idea.posts.all().order_by('-created_at')  # Сначала самые свежие
    
    context = {
        'idea': idea,
        'posts': posts,
    }
    
    return render(request, 'gen_posts_app/idea_posts.html', context)