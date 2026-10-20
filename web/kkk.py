import base64
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization

def generate_vapid_keys():
    print("⏳ Генерация ключей...")

    vapid = Vapid()
    vapid.generate_keys()

    # Публичный ключ — uncompressed point в base64url (без padding)
    public_key_bytes = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

    # !!! ВАЖНО: приватный ключ в DER, затем base64url
    private_key_der = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key_b64 = base64.urlsafe_b64encode(private_key_der).decode('utf-8').rstrip('=')

    print("\n" + "="*70)
    print("✅ СКОПИРУЙТЕ ЭТИ ЗНАЧЕНИЯ В ВАШ .env.prod:")
    print("="*70)
    print(f'VAPID_PUBLIC_KEY="{public_key_b64}"')
    print(f'VAPID_PRIVATE_KEY="{private_key_b64}"')
    print('VAPID_ADMIN_EMAIL="admin@sasha-sugar.ru"')
    print("="*70 + "\n")

if __name__ == "__main__":
    generate_vapid_keys()