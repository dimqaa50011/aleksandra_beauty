from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class BlogArticle(models.Model):
    """Модель для полноценных статей в блоге на сайте"""
    
    title = models.CharField('Заголовок', max_length=200)
    
    # Слаг для красивого URL (например: /blog/kak-uhazhivat-za-kozhey/)
    slug = models.SlugField('URL-адрес (слаг)', max_length=200, unique=True, blank=True, 
                            help_text="Оставьте пустым для автозаполнения из заголовка")
    
    # SEO
    seo_description = models.TextField('SEO-описание', blank=True, 
                                       help_text="Для поисковиков (до 160 символов)")
    
    # Контент
    image = models.ImageField('Обложка статьи', upload_to='blog/', blank=True, null=True)
    excerpt = models.TextField('Краткое описание (анонс)', max_length=300, blank=True, 
                               help_text="Показывается в списке статей")
    content = models.TextField('Текст статьи', help_text="Можно использовать HTML или Markdown")
    
    # Метаданные
    created_at = models.DateTimeField('Дата публикации', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    is_published = models.BooleanField('Опубликовано', default=True)
    
    # Просмотры (чтобы показывать "популярные статьи")
    views_count = models.PositiveIntegerField('Просмотры', default=0)

    class Meta:
        verbose_name = 'Статья блога'
        verbose_name_plural = 'Статьи блога'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматически генерируем слаг, если он не заполнен
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_app:blog_article_detail', kwargs={'slug': self.slug})

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