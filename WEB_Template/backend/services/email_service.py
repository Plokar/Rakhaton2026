"""
Email Service – Transactional Email Wrapper
V dev módu posílá do Mailhogu (http://localhost:8025).
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def send_hackathon_email(
    to: str,
    subject: str,
    body: str,
    html_body: str = None,
    from_email: str = None,
) -> bool:
    """Odešle e-mail zadanému příjemci"""
    sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hackathon.local')
    try:
        if html_body:
            msg = EmailMultiAlternatives(subject, body, sender, [to])
            msg.attach_alternative(html_body, "text/html")
            msg.send()
        else:
            send_mail(subject, body, sender, [to], fail_silently=False)

        logger.info(f"Email sent successfully to: {to} | Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False
