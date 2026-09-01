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
    """Главный экран — всё, что над услуг"""
    title = models.CharField(max_length=200, default="Раскрой своё природное сияние")
    subtitle = models.TextField(
        default="Уход за кожей, маникюр, педикюр и брови — всё в одном месте.",
        help_text="Описание под заголовком"
    )
    badge_text = models.CharField(max_length=50, default="✨ Новая коллекция", help_text="Маленький тег сверху")
    offer_text = models.CharField(max_length=200, default="🌸 20% OFF — для новых клиентов")
    button_text = models.CharField(max_length=50, default="Записаться сейчас")
    button_link = models.CharField(max_length=200, default="#", help_text="Ссылка на WhatsApp/Telegram")

    # Фото
    hero_image = models.ImageField(upload_to='hero/', blank=True, null=True, help_text="Фото мастера")

    # Статистика (3 блока)
    stat_1_number = models.CharField(max_length=20, default="10K+")
    stat_1_label = models.CharField(max_length=50, default="Довольных клиентов")

    stat_2_number = models.CharField(max_length=20, default="4.8")
    stat_2_label = models.CharField(max_length=50, default="★ Средний рейтинг")

    stat_3_number = models.CharField(max_length=20, default="98%")
    stat_3_label = models.CharField(max_length=50, default="Возвращаются")

    # Активен ли блок
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Герой (главный экран)"

    class Meta:
        verbose_name = "Герой"
        verbose_name_plural = "Герой"


# =============================================
# 3. КАТЕГОРИИ УСЛУГ (Shop By Category)
# =============================================
class ServiceCategory(models.Model):
    """Категории услуг — иконки в сетке 5 штук"""
    name = models.CharField(max_length=100, help_text="Маникюр")
    icon = models.CharField(max_length=10, help_text="💅 или другой эмодзи")
    description = models.CharField(max_length=100, blank=True, help_text="Гель, дизайн, уход")
    order = models.PositiveIntegerField(default=0, help_text="Порядок отображения (меньше — выше)")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Категория услуги"
        verbose_name_plural = "Категории услуг"

    def __str__(self):
        return self.name


# =============================================
# 4. УСЛУГИ (Карточки в блоке "Наши услуги")
# =============================================
class Service(models.Model):
    """Конкретная услуга — 4 карточки с фото, ценой, рейтингом"""
    # Связь с категорией (опционально)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services'
    )

    name = models.CharField(max_length=200, help_text="Премиум-маникюр")
    description = models.TextField(blank=True, help_text="Краткое описание")

    # Фото
    image = models.ImageField(upload_to='services/', blank=True, null=True)

    # Цены
    price = models.DecimalField(max_digits=10, decimal_places=0, default=2500, help_text="Текущая цена")
    old_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True, help_text="Старая цена (зачёркнутая)")

    # Рейтинг
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0, help_text="4.8, 5.0, и т.д.")
    reviews_count = models.PositiveIntegerField(default=0, help_text="Количество отзывов (109)")

    # Кнопка
    button_text = models.CharField(max_length=50, default="Запись")
    button_link = models.CharField(max_length=200, default="#", help_text="Ссылка на запись")

    # Отображение
    is_active = models.BooleanField(default=True)
    is_bestseller = models.BooleanField(default=False, help_text="Помечать как бестселлер (🔥)")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def __str__(self):
        return self.name


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
# 7. ОТЗЫВЫ
# =============================================
class Review(models.Model):
    """Отзывы клиентов"""
    client_name = models.CharField(max_length=100)
    client_avatar = models.ImageField(upload_to='reviews/', blank=True, null=True)
    text = models.TextField()
    rating = models.PositiveIntegerField(default=5, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"{self.client_name} — {self.rating}★"


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