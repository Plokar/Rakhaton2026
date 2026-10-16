from django.contrib import admin

from .models import BriefConfig, Decision, MdtCase, MdtSession, UserProfile

admin.site.register([BriefConfig, MdtSession, MdtCase, Decision, UserProfile])
