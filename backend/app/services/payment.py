import uuid
import logging
from typing import Any
from yookassa import Configuration, Payment
from app.config import settings

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        self.is_configured = bool(self.shop_id and self.secret_key)
        
        if self.is_configured:
            Configuration.account_id = self.shop_id
            Configuration.secret_key = self.secret_key
            logger.info("ЮKassa инициализирована с shop_id: %s", self.shop_id)
        else:
            logger.warning("ЮKassa учетные данные не заданы. Сервис работает в тестовом MOCK-режиме.")

    def create_sbp_payment(
        self,
        booking_id: int,
        deposit_amount: int,
        service_title: str,
        client_phone: str
    ) -> dict[str, Any]:
        """
        Создает платеж на сумму депозита через СБП.
        Возвращает payment_id и confirmation_url (deep-link для мобильного банка).
        """
        idempotency_key = str(uuid.uuid4())
        description = f"Депозит за слот бронирования #{booking_id}: {service_title[:60]}"
        return_url = f"{settings.MINI_APP_URL}?booking_id={booking_id}"

        if not self.is_configured:
            # Mock / Sandbox режим для локальной разработки и автотестов
            mock_payment_id = f"mock_{uuid.uuid4().hex[:12]}"
            mock_confirmation_url = f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={mock_payment_id}"
            return {
                "payment_id": mock_payment_id,
                "confirmation_url": mock_confirmation_url,
                "status": "pending"
            }

        try:
            payment_request = {
                "amount": {
                    "value": f"{deposit_amount}.00",
                    "currency": "RUB"
                },
                "payment_method_data": {
                    "type": "sbp"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "booking_id": booking_id
                }
            }

            payment = Payment.create(payment_request, idempotency_key)
            
            confirmation_url = ""
            if payment.confirmation and hasattr(payment.confirmation, "confirmation_url"):
                confirmation_url = payment.confirmation.confirmation_url
            elif hasattr(payment, "confirmation") and isinstance(payment.confirmation, dict):
                confirmation_url = payment.confirmation.get("confirmation_url", "")

            return {
                "payment_id": payment.id,
                "confirmation_url": confirmation_url or return_url,
                "status": payment.status
            }
        except Exception as e:
            logger.error("Ошибка при создании платежа в ЮKassa: %s", e)
            raise RuntimeError(f"Не удалось инициировать платеж через СБП: {e}")

payment_service = PaymentService()
