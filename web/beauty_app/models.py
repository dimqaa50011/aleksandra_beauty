from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# =============================================
# 1. НАСТРОЙКИ САЙТА
# =============================================
class SiteSettings(models.Model):
    """Основные настройки сайта (шапка, футер, контакты)"""
    site_name = models.CharField(max_length=100, default="Glowora")
    site_logo = models.ImageField(upload_to='logo/', blank=True, null=True, help_text="Загрузите логотип (прозрачный PNG)")

    # Контакты
    phone = models.CharField(max_length=20, blank=True, help_text="+7 (999) 123-45-67")
    whatsapp = models.CharField(max_length=20, blank=True, help_text="Ссылка на WhatsApp")
    telegram = models.CharField(max_length=100, blank=True, help_text="Ссылка на Telegram")
    email = models.EmailField(blank=True)

    # Адрес
    address = models.TextField(blank=True, help_text="Метро [Станция], 5 минут пешком")
    map_iframe = models.TextField(blank=True, help_text="iframe-код Яндекс.Карт")

    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True, max_length=500)

    # Соцсети
    instagram = models.URLField(blank=True)
    vk = models.URLField(blank=True)

    # Копирайт в футере
    footer_text = models.CharField(max_length=200, default="© 2026 — Бьюти-студия")

    def __str__(self):
        return self.site_name

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"


# =============================================
# 2. БЛОК ГЕРОЙ (ШАПКА)
# =============================================
class HeroBlock(models.Model):
    """Главный экран (Hero)"""
    title = models.CharField(max_length=200, default="Бьюти-студия Sasha Sugar в СПб: раскрой своё природное сияние")
    subtitle = models.TextField(
        default="Уход за кожей, аппаратная косметология, подбор домашнего ухода, депиляция, брови и ресницы — всё в одном месте.",
        help_text="Описание под заголовком"
    )
    button_text = models.CharField(max_length=50, default="Записаться сейчас")
    
    # Фото
    hero_image = models.ImageField(upload_to='hero/', blank=True, null=True, help_text="Фото для главного экрана")

    # Статистика (оставим 2 блока, как на макете)
    stat_1_number = models.CharField(max_length=20, default="5K+")
    stat_1_label = models.CharField(max_length=50, default="Довольных клиентов")

    stat_2_number = models.CharField(max_length=20, default="4.8")
    stat_2_label = models.CharField(max_length=50, default="★ Средний рейтинг")

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Герой (главный экран)"

    class Meta:
        verbose_name = "Герой"
        verbose_name_plural = "Герой"

class AboutBlock(models.Model):
    """Секция 'О нас'"""
    title = models.CharField(
        max_length=200, 
        default="Пространство, где о вас позаботятся",
        help_text="Заголовок блока"
    )
    text = models.TextField(
        default="Sasha Sugar — это студия в центре Петербурга, где не торопят и не навязывают лишнего. Мы работаем на премиальной косметике, используем стерильные инструменты и подбираем уход, который подходит именно вашей коже. Наши мастера не просто выполняют процедуру — они объясняют, что и зачем делают, и как поддерживать результат дома.",
        help_text="Основной текст"
    )
    
    image = models.ImageField(upload_to='about/', blank=True, null=True, help_text="Фото интерьера или мастера")

    # Преимущества без эмодзи
    feature_1 = models.CharField(max_length=150, default="Мастера с опытом от 5 лет — знаем, как не навредить")
    feature_2 = models.CharField(max_length=150, default="Премиальная косметика и стерильность на каждом этапе")
    feature_3 = models.CharField(max_length=150, default="Чай, тишина и никакой спешки — выходите отдохнувшими")

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Блок 'О нас'"

    class Meta:
        verbose_name = "Блок О нас"
        verbose_name_plural = "Блок О нас"
# =============================================
# 3. КАТЕГОРИИ УСЛУГ (Shop By Category)
# =============================================
class ServiceCategory(models.Model):
    """Категории услуг"""
    # Название для внутреннего пользования (в админке)
    name = models.CharField(max_length=100, help_text="Внутреннее название (например, 'Голени')")
    
    # Красивое название для сайта
    title = models.CharField(max_length=150, blank=True, help_text="Название для сайта (например, 'Депиляция голеней')")
    
    # SEO описание (для мета-тега description)
    seo_description = models.TextField(blank=True, help_text="Описание для поисковиков (до 160 символов)")

    icon = models.CharField(max_length=10, help_text="Эмодзи", blank=True, null=True)
    description = models.TextField(blank=True, help_text="Короткое описание для карточки на главной")
    order = models.PositiveIntegerField(default=0, help_text="Порядок отображения (меньше — выше)")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Обложка категории")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Категория услуги"
        verbose_name_plural = "Категории услуг"

    def __str__(self):
        return self.title if self.title else self.name

    @property
    def display_name(self):
        """Свойство, которое автоматически вернет красивое имя для сайта"""
        return self.title if self.title else self.name


class Service(models.Model):
    """Конкретная услуга"""
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services'
    )

    # Название для внутреннего пользования
    name = models.CharField(max_length=200, help_text="Внутреннее название (например, 'Голени')")
    
    # Красивое название для сайта (H1)
    title = models.CharField(max_length=250, blank=True, help_text="Название для сайта (например, 'Депиляция голеней воском')")
    
    # SEO описание (для мета-тега)
    seo_description = models.TextField(blank=True, help_text="Описание для поисковиков (до 160 символов)")

    # Текст на странице услуги
    description = models.TextField(blank=True, help_text="Основное описание услуги (с абзацами)")
    
    duration = models.PositiveSmallIntegerField("Длительность", default=15, help_text="В минутах")
    
    # Фото
    image = models.ImageField(upload_to='services/', blank=True, null=True)

    # Цены
    price = models.DecimalField(max_digits=10, decimal_places=0, default=2500, help_text="Текущая цена")
    old_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True, help_text="Старая цена (зачёркнутая)")

    # Рейтинг (оставим на будущее)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0, help_text="4.8, 5.0, и т.д.")
    reviews_count = models.PositiveIntegerField(default=0, help_text="Количество отзывов")

    # Кнопка
    button_text = models.CharField(max_length=50, default="Записаться", help_text="Текст на кнопке")
    
    # Отображение
    is_active = models.BooleanField(default=True)
    is_bestseller = models.BooleanField(default=False, help_text="Помечать как бестселлер (🔥)")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def __str__(self):
        return self.title if self.title else self.name

    @property
    def display_name(self):
        """Красивое имя для вывода на сайте"""
        return self.title if self.title else self.name
class HeroSlide(models.Model):
    """Фоновые картинки для главного экрана (слайдер)"""
    image = models.ImageField(upload_to='hero_slides/', help_text="Рекомендуемый размер: 1920x1080")
    order = models.PositiveIntegerField(default=0, help_text="Порядок (меньше — выше)")
    is_active = models.BooleanField(default=True, help_text="Показывать этот слайд")

    class Meta:
        ordering = ['order']
        verbose_name = 'Слайд главного экрана'
        verbose_name_plural = 'Слайды главного экрана'

    def __str__(self):
        return f"Слайд {self.id}"
    
class MasterBlock(models.Model):
    """Блок о мастере (личный бренд)"""
    name = models.CharField(max_length=100, default="Александра Сахарова")
    title = models.CharField(max_length=150, default="Основатель студии, топ-мастер")
    text = models.TextField(
        default="Меня зовут Александра. Я создала Sasha Sugar, чтобы каждая девушка могла доверить свою красоту профессионалу и просто выдохнуть. Работаю с кожей и бровями уже более 5 лет. Постоянно учусь, слежу за трендами и использую только те материалы, в которых уверена на 100%.",
        help_text="Текст о мастере"
    )
    
    # Фото мастера
    image = models.ImageField(upload_to='masters/', blank=True, null=True, help_text="Портретное фото")
    
    # Ссылки на соцсети (если нужно)
    link_telegram = models.URLField(blank=True, null=True, help_text="Ссылка на Telegram")
    link_vk = models.URLField(blank=True, null=True, help_text="Ссылка на VK")

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Блок Мастера"
        verbose_name_plural = "Блок Мастера"

class Review(models.Model):
    """Отзывы клиентов"""
    # Связь с записью (один отзыв на одну запись)
    booking = models.OneToOneField(
        "booking_app.Booking", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='review',
        verbose_name='Запись'
    )

    author_name = models.CharField(max_length=100, help_text="Имя клиента")
    text = models.TextField(help_text="Текст отзыва")
    service_name = models.CharField(max_length=100, blank=True, help_text="На какую услугу отзыв")
    
    # Оценка (звезды)
    rating = models.PositiveSmallIntegerField(default=5, choices=[(i, str(i)) for i in range(1, 6)], help_text="Оценка от 1 до 5")
    
    # Дата
    created_at = models.DateTimeField(auto_now_add=True, help_text="Дата отзыва")
    
    # Ссылка на оригинал (если админ копирует отзыв с Яндекса)
    source_url = models.URLField(blank=True, null=True, help_text="Ссылка на оригинал (если есть)")

    # Модерация: по умолчанию False (скрыт), админ включит в приложении
    is_active = models.BooleanField(default=False, help_text="Опубликован на сайте")
    is_read = models.BooleanField('Прочитано админом', default=False)

    def __str__(self):
        status = "Опубликован" if self.is_active else "На модерации"
        return f"{self.author_name} — {self.rating}★ ({status})"

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']
# =============================================
# 5. БАННЕР С АКЦИЕЙ
# =============================================
class Banner(models.Model):
    """Большой баннер с акцией (20% OFF)"""
    title = models.CharField(max_length=200, default="Уход, который любит тебя")
    subtitle = models.CharField(max_length=200, default="Скидка 20% на наши бестселлеры. Предложение ограничено!")
    badge_text = models.CharField(max_length=50, default="20% OFF", help_text="Крупная цифра на баннере")
    badge_small = models.CharField(max_length=50, default="OFF", help_text="Маленький текст рядом с цифрой")

    button_text = models.CharField(max_length=50, blank=True, help_text="Кнопка на баннере (опционально)")
    button_link = models.CharField(max_length=200, blank=True)

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def __str__(self):
        return self.title


# =============================================
# 6. БЛОК ДОВЕРИЯ (Trust / Stats)
# =============================================
class TrustBlock(models.Model):
    """Блок со статистикой (4.8 ★ / 10K+ / 98%)"""
    title = models.CharField(max_length=200, default="Красота, которая любит тебя")
    subtitle = models.CharField(max_length=200, default="Скидка 20% на наши бестселлеры")

    # Статистика
    stat_1_number = models.CharField(max_length=20, default="4.8")
    stat_1_label = models.CharField(max_length=50, default="Средний рейтинг")
    stat_1_extra = models.CharField(max_length=20, default="★★★★★", help_text="Звёздочки")

    stat_2_number = models.CharField(max_length=20, default="10K+")
    stat_2_label = models.CharField(max_length=50, default="Довольных клиентов")

    stat_3_number = models.CharField(max_length=20, default="98%")
    stat_3_label = models.CharField(max_length=50, default="Возвращаются")

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Блок доверия"

    class Meta:
        verbose_name = "Блок доверия"
        verbose_name_plural = "Блок доверия"


# =============================================


# =============================================
# 8. НАВИГАЦИЯ (Меню)
# =============================================
class MenuItem(models.Model):
    """Пункты меню в шапке"""
    title = models.CharField(max_length=50)
    url = models.CharField(max_length=200, default="#", help_text="Ссылка или якорь #id")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Пункт меню"
        verbose_name_plural = "Пункты меню"

    def __str__(self):
        return self.title


# =============================================
# 9. ССЫЛКИ В ФУТЕРЕ
# =============================================
class FooterLink(models.Model):
    """Ссылки в футере"""
    title = models.CharField(max_length=50)
    url = models.CharField(max_length=200, default="#")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Ссылка в футере"
        verbose_name_plural = "Ссылки в футере"

    def __str__(self):
        return self.title


class FAQ(models.Model):
    """Часто задаваемые вопросы"""
    question = models.CharField('Вопрос', max_length=300)
    answer = models.TextField('Ответ')
    order = models.PositiveIntegerField('Порядок отображения', default=0, help_text="Меньшее число = выше в списке")
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Часто задаваемый вопрос'
        verbose_name_plural = 'Часто задаваемые вопросы'
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.question