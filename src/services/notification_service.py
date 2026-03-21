import logging
import os
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                logger.warning("Twilio credentials not configured — notifications disabled")
                return None
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def send_whatsapp(self, to_phone: str, message: str) -> bool:
        """Send a WhatsApp message via Twilio. Returns True on success."""
        client = self.client
        if not client:
            logger.warning("Skipping WhatsApp notification to %s — no Twilio client", to_phone)
            return False
        try:
            # Ensure number is in whatsapp: format
            if not to_phone.startswith('whatsapp:'):
                to_phone = f'whatsapp:{to_phone}'
            from_wa = f'whatsapp:{self.from_number}'
            client.messages.create(body=message, from_=from_wa, to=to_phone)
            logger.info("WhatsApp sent to %s", to_phone)
            return True
        except Exception as e:
            logger.error("Failed to send WhatsApp to %s: %s", to_phone, e)
            return False

    def broadcast_job(self, job, provider_phones: set) -> int:
        """Broadcast a job request to a set of provider phone numbers. Returns count sent."""
        if not provider_phones:
            return 0
        message = (
            f"📢 *New {job.category.title()} Job in {job.location}*\n\n"
            f"_{job.description}_\n\n"
            f"Reply with your details to win this job!\n"
            f"📍 Posted via LinkUp Geo"
        )
        sent = 0
        for phone in provider_phones:
            if self.send_whatsapp(phone, message):
                sent += 1
        return sent


notification_service = NotificationService()
