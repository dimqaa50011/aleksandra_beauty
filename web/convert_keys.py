from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64

# Читаем приватный ключ из PEM
with open('private_key.pem', 'rb') as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# Конвертируем приватный ключ
private_int = private_key.private_numbers().private_value
private_bytes = private_int.to_bytes(32, byteorder='big')
private_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('utf-8')

# Конвертируем публичный ключ
public_numbers = private_key.public_key().public_numbers()
x = public_numbers.x.to_bytes(32, byteorder='big')
y = public_numbers.y.to_bytes(32, byteorder='big')
public_bytes = b'\x04' + x + y
public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('utf-8')

print(f'VAPID_PRIVATE_KEY={private_b64}')
print(f'VAPID_PUBLIC_KEY={public_b64}')