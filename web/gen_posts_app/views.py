from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django_q.tasks import async_task
from .models import PostIdea, PostContent
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy

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

def blog_list(request):
    """Публичная страница блога со списком постов"""
    # Показываем только одобренные посты, от новых к старым
    posts = PostContent.objects.filter(is_approved=True).order_by('-created_at')
    
    return render(request, 'gen_posts_app/blog_list.html', {'posts': posts})


def blog_post_detail(request, post_id):
    """Публичная страница полного просмотра одного поста"""
    # get_or_404 гарантирует, что мы покажем только одобренный пост
    post = get_object_or_404(PostContent, id=post_id, is_approved=True)
    
    return render(request, 'gen_posts_app/blog_post_detail.html', {'post': post})

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('beauty_app:login')
    permission_denied_message = 'Доступ запрещён. Требуются права администратора.'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'beauty_app/auth/access_denied.html', status=403)
        return redirect(self.login_url)

class UpdatePostStatusView(AdminRequiredMixin, View):
    """Изменение статуса поста (одобрить / опубликовать / вернуть в черновики)"""
    
    def post(self, request, idea_id, post_id):
        post = get_object_or_404(PostContent, id=post_id, idea_id=idea_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            post.is_approved = True
            post.is_published = False
            post.save()
            messages.success(request, f'✅ Пост "{post.variant_name}" одобрен')
            
        elif action == 'publish':
            if not post.is_approved:
                messages.error(request, 'Сначала нужно одобрить пост')
            else:
                post.is_published = True
                post.save()
                messages.success(request, f'🚀 Пост опубликован и доступен в блоге')
                
        elif action == 'unpublish':
            post.is_published = False
            post.save()
            messages.success(request, f'Пост скрыт из блога')
            
        elif action == 'draft':
            post.is_approved = False
            post.is_published = False
            post.save()
            messages.success(request, f'Пост возвращён в черновики')
        
        return redirect('gen_posts_app:idea_posts', idea_id=idea_id)