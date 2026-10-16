"""Utility funkce sdílené napříč aplikací"""
from typing import Dict, Any


def serialize_model(instance) -> Dict[str, Any]:
    """Jednoduchá serializace modelu do dict"""
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        data[field.name] = value
    return data
