from pywebpush import webpush, WebPushException
import json

# Генерируем ключи (запусти один раз)
from py_vapid import Vapid
vapid = Vapid()
vapid.generate_keys()

print("PRIVATE_KEY:")
print(vapid.private_pem)
print("\nPUBLIC_KEY:")
print(vapid.public_pem)