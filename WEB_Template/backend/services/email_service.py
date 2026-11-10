"""E-maily aplikace (pozvánky, obnova hesla). Dev: Mailhog (http://localhost:8025); bez SMTP do konzole (T-371)."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str, html_body: str | None = None, from_email: str | None = None) -> bool:
    """Odešle e-mail; `False` když se nepodařilo (volající nabídne odkaz ke zkopírování). Adresu příjemce nelogujeme."""
    sender = from_email or settings.DEFAULT_FROM_EMAIL
    if settings.EMAIL_BACKEND.endswith('console.EmailBackend'):     # bez SMTP: jen do výpisu, adresát nic nedostane
        logger.warning('E-mail neodeslán (bez SMTP): %s', subject)
        return False
    try:
        if html_body:
            msg = EmailMultiAlternatives(subject, body, sender, [to])
            msg.attach_alternative(html_body, 'text/html')
            msg.send()
        else:
            send_mail(subject, body, sender, [to], fail_silently=False)
        logger.info('E-mail odeslán: %s', subject)
        return True
    except Exception as e:
        logger.error('E-mail se nepodařilo odeslat (%s): %s', subject, type(e).__name__)
        return False
