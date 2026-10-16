"""Core exceptions pro aplikaci"""


class ServiceException(Exception):
    """Základní výjimka pro servisní vrstvu"""
    pass


class NotFoundException(ServiceException):
    """Výjimka pro nenalezené entity"""
    pass


class ValidationException(ServiceException):
    """Výjimka pro validační chyby"""
    pass


def custom_exception_handler(exc, context):
    """
    Vlastní exception handler pro Django Rest Framework.
    Sjednocuje formát chybových odpovědí.
    """
    from rest_framework.views import exception_handler
    from rest_framework.response import Response
    from rest_framework import status
    import logging

    logger = logging.getLogger(__name__)

    response = exception_handler(exc, context)

    if response is not None:
        return response

    logger.error(f"Unhandled exception in API view: {exc}", exc_info=True)
    return Response(
        {
            "detail": "Vyskytla se interní chyba serveru.",
            "error": str(exc),
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

