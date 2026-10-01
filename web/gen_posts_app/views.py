from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django_q.tasks import async_task
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
    """Отдельная вьюха для запуска генерации в фоне"""
    
    idea = get_object_or_404(PostIdea, id=idea_id)
    
    if request.method == 'POST':
        # Отправляем задачу в фоновую очередь!
        # Первый аргумент - строка с путем к функции, второй - аргументы
        async_task('gen_posts_app.tasks.generate_post_task', idea.id)
        
        messages.success(request, f'⏳ Генерация для "{idea.topic}" запущена в фоне!')
    
    return redirect('gen_posts_app:idea_posts', idea_id=idea.id)