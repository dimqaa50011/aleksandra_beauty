from django.db import models


class PostIdea(models.Model):
    """Таблица идей для постов"""
    
    STATUS_CHOICES = [
        ('new', '🆕 Новая'),
        ('in_progress', '⚙️ В работе'),
        ('ready', '✅ Готова к публикации'),
        ('published', ' Опубликована'),
        ('archived', '📦 В архиве'),
    ]
    
    PLATFORM_CHOICES = [
        ('telegram', 'Telegram'),
        ('vk', 'ВКонтакте'),
        ('both', 'Обе платформы'),
    ]
    
    topic = models.CharField('Тема поста', max_length=200)
    description = models.TextField('Описание/контекст', blank=True, help_text='Что важно упомянуть? Какие детали?')
    platform = models.CharField('Платформа', max_length=20, choices=PLATFORM_CHOICES, default='telegram')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Идея поста'
        verbose_name_plural = 'Идеи постов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.topic} ({self.get_status_display()})'
    
    def get_posts_count(self):
        """Количество сгенерированных постов для этой идеи"""
        return self.posts.count()


class PostContent(models.Model):
    """Таблица сгенерированного контента (может быть несколько на одну идею)"""
    
    idea = models.ForeignKey(
        PostIdea, 
        on_delete=models.CASCADE, 
        related_name='posts',
        verbose_name='Идея'
    )
    
    variant_name = models.CharField('Название варианта', max_length=100, blank=True, help_text='Например: "Вариант 1", "Часть 1 из 3", "Для Telegram"')
    
    headline = models.CharField('Заголовок', max_length=200, blank=True)
    body = models.TextField('Текст поста', blank=True)
    hashtags = models.CharField('Хештеги', max_length=300, blank=True)
    
    is_approved = models.BooleanField('Одобрено', default=False)
    is_published = models.BooleanField('Опубликовано', default=False)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Контент поста'
        verbose_name_plural = 'Контент постов'
        ordering = ['-created_at']
    
    def __str__(self):
        variant = f' - {self.variant_name}' if self.variant_name else ''
        return f'{self.idea.topic}{variant}'