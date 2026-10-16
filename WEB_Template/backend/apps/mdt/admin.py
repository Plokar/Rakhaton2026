from django.contrib import admin

from .models import BriefConfig, MdtCase, MdtSession

admin.site.register([BriefConfig, MdtSession, MdtCase])
