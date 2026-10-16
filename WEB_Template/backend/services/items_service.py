"""Service layer pro Items modul - business logika oddělená od views"""
from typing import List, Dict, Any
from apps.items.models import Item
from core.utils import serialize_model
from core.exceptions import NotFoundException


class ItemsService:
    """Servisní třída pro práci s Items"""
    
    @staticmethod
    def get_all_items() -> List[Dict[str, Any]]:
        """Získat všechny položky"""
        items = Item.objects.all()
        return [serialize_model(item) for item in items]
    
    @staticmethod
    def get_item_by_id(item_id: int) -> Dict[str, Any]:
        """Získat položku podle ID"""
        try:
            item = Item.objects.get(pk=item_id)
            return serialize_model(item)
        except Item.DoesNotExist:
            raise NotFoundException(f"Item with id {item_id} not found")
    
    @staticmethod
    def create_item(name: str, description: str = "") -> Dict[str, Any]:
        """Vytvořit novou položku"""
        item = Item.objects.create(name=name, description=description)
        return serialize_model(item)
    
    @staticmethod
    def update_item(item_id: int, **kwargs) -> Dict[str, Any]:
        """Aktualizovat položku"""
        try:
            item = Item.objects.get(pk=item_id)
            for key, value in kwargs.items():
                setattr(item, key, value)
            item.save()
            return serialize_model(item)
        except Item.DoesNotExist:
            raise NotFoundException(f"Item with id {item_id} not found")
    
    @staticmethod
    def delete_item(item_id: int) -> None:
        """Smazat položku"""
        try:
            item = Item.objects.get(pk=item_id)
            item.delete()
        except Item.DoesNotExist:
            raise NotFoundException(f"Item with id {item_id} not found")
