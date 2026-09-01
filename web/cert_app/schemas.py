from typing import Optional

from ninja import Schema


class CreateCertSchema(Schema):
    phone: str
    email: str
    price: float
    first_name: str
    last_name: Optional[str] = None