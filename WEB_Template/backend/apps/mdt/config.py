"""Konfigurace podkladu (FR-R1, ARCH §8.5): validace, výchozí konfigurace a presety."""
from rest_framework import serializers

from .models import DETAIL_LEVELS, BriefConfig

# výchozí pořadí bloků (ARCH §7.3 bod 9)
SECTION_ORDER = ('summary', 'timeline', 'red_flags', 'anamnesis', 'role_views', 'modalities',
                 'decision_support', 'trials', 'questions', 'mdt_question')
ROLE_IDS = {'surgeon', 'oncologist', 'radiation_oncologist', 'radiologist', 'pathologist', 'pulmonologist',
            'cardiologist', 'patient',
            # další role (BONUS zadání B, T-332)
            'nuclear_medicine', 'palliative_care', 'geriatrician', 'geneticist', 'coordinator'}
DETAILS = {d for d, _ in DETAIL_LEVELS}


def _sections(enabled=SECTION_ORDER) -> list[dict]:
    return [{'id': s, 'enabled': s in enabled, 'order': i} for i, s in enumerate(SECTION_ORDER)]


DEFAULT_CONFIG = {'name': 'Výchozí', 'sections': _sections(),
                  'roles_present': ['oncologist', 'surgeon', 'radiologist', 'pathologist', 'patient'],
                  'detail_level': 'standard', 'language': 'cs', 'hide_unverified': False, 'disabled_rules': []}

PRESETS = [
    {**DEFAULT_CONFIG, 'name': 'Standardní podklad'},
    {**DEFAULT_CONFIG, 'name': 'Stručně (30 s)', 'detail_level': 'brief',
     'sections': _sections(('summary', 'red_flags', 'decision_support', 'mdt_question'))},
]


class BriefConfigSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    language = serializers.ChoiceField(['cs', 'sk', 'en'], default='cs')

    class Meta:
        model = BriefConfig
        fields = ['id', 'name', 'is_preset', 'sections', 'roles_present', 'detail_level', 'language', 'hide_unverified',
                  'disabled_rules']

    def get_id(self, obj) -> str:
        return str(obj.pk)

    def validate_sections(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Seznam sekcí.')
        for s in value:
            if not isinstance(s, dict) or s.get('id') not in SECTION_ORDER \
                    or not isinstance(s.get('enabled'), bool) or not isinstance(s.get('order'), int) \
                    or s.get('detail', 'standard') not in DETAILS:
                raise serializers.ValidationError(f'Neplatná sekce {s!r} (ARCH §8.5, SectionId §8.1).')
        return value

    def validate_roles_present(self, value):
        if not isinstance(value, list) or not set(value) <= ROLE_IDS:
            raise serializers.ValidationError(f'Role jen z RoleId: {sorted(ROLE_IDS)}.')
        return value

    def validate_disabled_rules(self, value):
        from services.rules.red_flags import RULE_CATALOG

        if not isinstance(value, list) or not set(value) <= set(RULE_CATALOG):
            raise serializers.ValidationError(f'Pravidla jen z katalogu: {sorted(RULE_CATALOG)}.')
        return sorted(set(value))


def validated(data: dict) -> dict:
    """Konfigurace z UI → validovaný snapshot (jde do promptů, proto striktně)."""
    s = BriefConfigSerializer(data={**DEFAULT_CONFIG, **data})
    s.is_valid(raise_exception=True)
    return {k: v for k, v in s.validated_data.items() if k != 'is_preset'}


def ensure_presets(owner) -> None:
    """Presety „Standardní podklad“, „Stručně (30 s)“ a šablony projektoru z báze `data/onko/sablony.tsv` (T-318)."""
    from services.rules.templates import template_presets

    for preset in PRESETS + [validated(t) for t in template_presets()]:
        BriefConfig.objects.get_or_create(name=preset['name'], is_preset=True,
                                          defaults={**preset, 'owner': owner})
