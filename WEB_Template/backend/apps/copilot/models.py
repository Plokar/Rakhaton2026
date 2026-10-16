"""Výstupy AI a joby generování (ARCH §6.2)."""
from django.conf import settings
from django.db import models


class Brief(models.Model):
    """Vygenerovaný podklad (obsah = schéma Brief, ARCH §8.2)."""
    case = models.ForeignKey('mdt.MdtCase', on_delete=models.CASCADE, related_name='briefs')
    config_snapshot = models.JSONField(default=dict)
    content = models.JSONField()
    model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GenerationJob(models.Model):
    """Asynchronní generování (D-004): FE polluje `GET /api/jobs/{id}/`."""
    KIND = [('brief', 'podklad'), ('scribe', 'zapisovatel'), ('patient_summary', 'shrnutí pro pacienta')]
    STATUS = [('queued', 've frontě'), ('running', 'běží'), ('done', 'hotovo'), ('error', 'chyba')]
    case = models.ForeignKey('mdt.MdtCase', on_delete=models.CASCADE, related_name='jobs')
    kind = models.CharField(max_length=20, choices=KIND)
    status = models.CharField(max_length=10, choices=STATUS, default='queued')
    progress = models.PositiveSmallIntegerField(default=0)       # 0–100
    params = models.JSONField(default=dict, blank=True)          # {"config": BriefConfig snapshot}
    result_id = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LlmCallLog(models.Model):
    """Audit volání LLM (NFR-4). Prompt se neukládá, jen hash."""
    purpose = models.CharField(max_length=50)                    # "brief.summary", "brief.role.surgeon", "rf_llm"…
    provider = models.CharField(max_length=20)
    model = models.CharField(max_length=100, blank=True)
    prompt_hash = models.CharField(max_length=64, blank=True)
    tokens_in = models.PositiveIntegerField(null=True, blank=True)
    tokens_out = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def record(cls, purpose: str, result: dict) -> 'LlmCallLog':
        """Uloží výsledek `provider.generate()` (dict ze `services/ai_service.py`)."""
        return cls.objects.create(
            purpose=purpose, provider=result.get('provider', ''), model=result.get('model', ''),
            prompt_hash=result.get('prompt_hash', ''), tokens_in=result.get('tokens_in'),
            tokens_out=result.get('tokens_out'), latency_ms=result.get('latency_ms'),
            ok=result.get('status') == 'success', error=result.get('error', ''),
        )
