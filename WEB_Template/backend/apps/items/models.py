from django.db import models
from core.models import TimeStampedModel


class Item(TimeStampedModel):
    """Item model - příklad doménového modelu"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'items'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
