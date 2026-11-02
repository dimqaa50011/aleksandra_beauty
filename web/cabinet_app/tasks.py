from .services.push import send_bulk_push_to_clients

def task_send_bulk_push(client_ids: list[int], title: str, body: str, url: str = '/cabinet/'):
    """Обертка для Django-Q."""
    send_bulk_push_to_clients(client_ids, title, body, url)