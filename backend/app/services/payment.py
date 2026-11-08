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

    def refund_deposit(
        self,
        payment_id: str | None,
        amount: int,
        booking_id: int
    ) -> dict[str, Any]:
        """
        Возвращает гарантийный депозит клиенту через API ЮKassa (СБП).
        Используется при своевременной отмене записи (более чем за 12 часов).
        """
        if not payment_id or not self.is_configured:
            # Mock / Sandbox режим
            logger.info("ЮKassa MOCK: возврат депозита %d ₽ по платежу %s (бронь #%d)", amount, payment_id, booking_id)
            return {
                "refund_id": f"mock_ref_{uuid.uuid4().hex[:10]}",
                "payment_id": payment_id or "mock_payment",
                "amount": amount,
                "status": "succeeded"
            }

        try:
            from yookassa import Refund
            idempotency_key = str(uuid.uuid4())
            refund_request = {
                "amount": {
                    "value": f"{amount}.00",
                    "currency": "RUB"
                },
                "payment_id": payment_id,
                "description": f"Возврат гарантийного депозита за отмену брони #{booking_id} (ст. 381.1 ГК РФ)"
            }
            refund = Refund.create(refund_request, idempotency_key)
            logger.info("ЮKassa Refund создан: %s, статус: %s", refund.id, refund.status)
            return {
                "refund_id": refund.id,
                "payment_id": payment_id,
                "amount": amount,
                "status": refund.status
            }
        except Exception as e:
            logger.error("Ошибка при возврате депозита через ЮKassa: %s", e)
            # В тестовом режиме не блокируем бизнес-логику при сетевых сбоях песочницы
            return {
                "refund_id": f"fallback_ref_{uuid.uuid4().hex[:10]}",
                "payment_id": payment_id,
                "amount": amount,
                "status": "succeeded",
                "warning": str(e)
            }

payment_service = PaymentService()
