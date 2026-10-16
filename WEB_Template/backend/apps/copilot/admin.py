from django.contrib import admin

from .models import Brief, GenerationJob, LlmCallLog

admin.site.register([Brief, GenerationJob, LlmCallLog])
