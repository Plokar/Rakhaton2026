"""Stav aplikace MDT v Postgresu (ARCH §6.2). Klinická data zůstávají v IRIS, tady jsou jen FHIR ID."""
from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

DETAIL_LEVELS = [('brief', 'stručně'), ('standard', 'standardně'), ('detailed', 'podrobně')]


class BriefConfig(models.Model):
    """Konfigurace podkladu / preset (ARCH §8.5)."""
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    is_preset = models.BooleanField(default=False)
    sections = models.JSONField(default=list, blank=True)        # [{id, enabled, order, detail}]
    roles_present = models.JSONField(default=list, blank=True)   # [RoleId]
    detail_level = models.CharField(max_length=10, choices=DETAIL_LEVELS, default='standard')
    language = models.CharField(max_length=2, default='cs')
    hide_unverified = models.BooleanField(default=False)

    def snapshot(self) -> dict:
        return {
            'id': str(self.pk), 'name': self.name, 'sections': self.sections, 'roles_present': self.roles_present,
            'detail_level': self.detail_level, 'language': self.language, 'hide_unverified': self.hide_unverified,
        }

    def __str__(self):
        return self.name


class MdtSession(models.Model):
    """Zasedání MDT = board (D-014). Zakládá a mění jen `mdt_admin` (T-501)."""
    STATUS = [('planned', 'plánováno'), ('in_progress', 'probíhá'), ('closed', 'uzavřeno')]
    date = models.DateTimeField()
    title = models.CharField(max_length=300)                     # zaměření komise
    chair = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='chaired_sessions')
    status = models.CharField(max_length=12, choices=STATUS, default='planned')
    config = models.ForeignKey(BriefConfig, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['date', 'title']

    def __str__(self):
        return f'{self.date:%Y-%m-%d %H:%M} {self.title}'


class MdtCase(models.Model):
    """Pacient zařazený do boardu (ARCH §6.2, §8.6)."""
    STATUS = [('nominated', 'nominován'), ('ready', 'připraven'), ('in_discussion', 'projednává se'),
              ('decided', 'rozhodnuto'), ('confirmed', 'potvrzeno'), ('returned', 'vráceno k doplnění')]
    INTENT = [('C', 'kurativní'), ('P', 'paliativní')]
    session = models.ForeignKey(MdtSession, on_delete=models.CASCADE, related_name='cases')
    order = models.PositiveSmallIntegerField(default=0)
    patient_fhir_id = models.CharField(max_length=16)            # "P03"
    service_request_fhir_id = models.CharField(max_length=64)    # "P03-zad01"
    question = models.TextField(blank=True)
    status = models.CharField(max_length=14, choices=STATUS, default='nominated')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='created_cases')
    # Přizvaní ke spolupráci (T-326): smějí případ upravovat jako zadávající lékař; přizývá předseda nebo zadávající.
    collaborators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='mdt_collaborations')
    ecog = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(4)])
    intent = models.CharField(max_length=1, choices=INTENT, null=True, blank=True)
    imaging_recent_checked = models.BooleanField(default=False)
    skipped_fields = models.JSONField(default=list, blank=True)          # [IntakeField.id]
    acknowledged_warnings = models.JSONField(default=list, blank=True)   # [{id, by, at}]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['session', 'order', 'id']

    def __str__(self):
        return f'{self.patient_fhir_id} @ {self.session}'


class UserProfile(models.Model):
    """Odbornost uživatele (hodnoty `RoleId`, ARCH §8.1). Role = Django `Group` (D-014)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mdt_profile')
    specialty = models.CharField(max_length=30, blank=True)     # "oncologist" | "surgeon" | "pulmonologist"…

    def __str__(self):
        return f'{self.user} ({self.specialty})'


class Decision(models.Model):
    """Závěr komise (obsah = schéma Decision, ARCH §8.4). Po potvrzení je v IRIS a dál se nemění."""
    STATUS = [('draft', 'návrh'), ('confirmed', 'potvrzeno')]
    case = models.OneToOneField(MdtCase, on_delete=models.CASCADE, related_name='decision')
    content = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    fhir_ids = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PatientDraft(models.Model):
    """Návrh nového pacienta (T-323): RČ, podklady a nominace před potvrzením do IRIS.

    Po potvrzení jsou data v IRIS; z návrhu se RČ a texty podkladů smažou (zůstane jen ID pacienta a případu).
    """
    STATUS = [('draft', 'návrh'), ('confirmed', 'potvrzeno')]
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name='patient_drafts')
    patient_fhir_id = models.CharField(max_length=16)            # přidělené „P07“
    rc = models.CharField(max_length=11, blank=True)             # „RRMMDD/XXXX“; po potvrzení prázdné
    synthetic = models.BooleanField(default=False)               # testovací pacient (D-021: smí do free tieru)
    session = models.ForeignKey(MdtSession, null=True, blank=True, on_delete=models.SET_NULL)
    content = models.JSONField(default=dict, blank=True)         # documents, fields, edited, values, rejected, ai
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    case = models.ForeignKey(MdtCase, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.patient_fhir_id} ({self.get_status_display()})'
