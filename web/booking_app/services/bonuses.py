
from ..models import Booking, Client

def set_bonuses(client: Client, bonus_amount: int, booking: Booking):
    if bonus_amount <= 0:
        return
    from cabinet_app.services.bonuses import accrue_bonuses
    accrue_bonuses(client, bonus_amount, "Кэшбек", booking=booking)

def spend_bonuses_booking(client: Client, amount: int, booking: Booking):
    from cabinet_app.services.bonuses import spend_bonuses
    spend_bonuses(
        client, amount, "Списание бонусов", booking=booking
    )