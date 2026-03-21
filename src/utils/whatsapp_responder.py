"""WhatsApp response formatting helpers."""
from twilio.twiml.messaging_response import MessagingResponse


def build_twiml(message: str) -> str:
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)
