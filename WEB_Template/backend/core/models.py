from django.db import models


class TimeStampedModel(models.Model):
    """Abstraktní model s časovými razítky"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
