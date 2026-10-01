import time
from .models import PostIdea, PostContent


def call_gigachat_api(topic: str, description: str) -> dict:
    """
    Заглушка для запроса к GigaChat API.
    В будущем здесь будет реальный HTTP-запрос к нейросети.
    
    Сигнатура: принимает тему и описание, возвращает словарь с текстом.
    """
    # Имитация задержки сети и генерации (2 секунды)
    time.sleep(2)
    
    # Имитация ответа от нейросети
    return {
        "headline": f"✨ {topic}: секреты и рекомендации от Sasha Sugar",
        "body": (
            f"Девочки, сегодня хотим поговорить о том, как правильно подходить к теме: "
            f"{topic.lower()}. \n\n"
            f"Контекст и важные детали: {description}. \n\n"
            f"Это очень важно для вашей красоты и здоровья! "
            f"Приходите к нам в студию на Спасский переулок, 7, и мы подберем "
            f"идеальный уход именно для вас."
        ),
        "hashtags": "#sashasugar #spb #beauty #косметологияспб #спасский7"
    }


def generate_post_task(idea_id: int):
    """
    Фоновая задача для генерации поста.
    Принимает ID идеи, делает запрос к API и сохраняет результат в базу.
    """
    try:
        idea = PostIdea.objects.get(id=idea_id)
    except PostIdea.DoesNotExist:
        print(f"Ошибка: Идея с id={idea_id} не найдена.")
        return

    # 1. Делаем запрос к нейросети (пока вызываем заглушку)
    response = call_gigachat_api(idea.topic, idea.description)

    # 2. Сохраняем сгенерированный контент
    PostContent.objects.create(
        idea=idea,
        variant_name=f"Вариант {idea.posts.count() + 1}",
        headline=response["headline"],
        body=response["body"],
        hashtags=response["hashtags"],
        is_approved=False,
        is_published=False
    )

    # 3. Обновляем статус идеи
    idea.status = 'in_progress'
    idea.save()