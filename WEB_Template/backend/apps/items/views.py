from django.http import JsonResponse
from django.views import View
from .models import Item
from services.items_service import ItemsService


class ItemListView(View):
    """API endpoint pro seznam položek"""
    
    def get(self, request):
        items = ItemsService.get_all_items()
        return JsonResponse({
            'count': len(items),
            'results': items
        })


def item_detail(request, pk):
    """API endpoint pro detail položky"""
    try:
        item = ItemsService.get_item_by_id(pk)
        return JsonResponse(item)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
