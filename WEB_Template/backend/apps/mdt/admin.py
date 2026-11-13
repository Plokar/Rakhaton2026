from django.contrib import admin

from .models import AccessLog, BriefConfig, Decision, MdtCase, MdtSession, UserProfile

admin.site.register([BriefConfig, MdtSession, MdtCase, Decision, UserProfile])


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    """Záznam přístupů (T-370) jen pro čtení: nikdo ho z adminu nezmění ani nesmaže."""
    list_display = ('created_at', 'username', 'action', 'patient_fhir_id', 'case', 'status_code', 'path')
    list_filter = ('action', 'created_at', 'username')
    search_fields = ('patient_fhir_id', 'username', 'path')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
