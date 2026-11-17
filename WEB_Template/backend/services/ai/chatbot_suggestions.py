"""Navržené otázky pro chatbot podle diagnózy (T-382).

Lékař na jednání často neví, na co se dá AI ptát. Otázky jsou podle oblasti šablony (`area_for_icd10`, stejné
pravidlo jako sady guidelines) a míří na údaje, které v dokumentaci bývají a komise je řeší. Nic se tu negeneruje
jazykovým modelem: seznam je pevný a dohledatelný.
"""
from __future__ import annotations

SUGGESTIONS: dict[str, list[str]] = {
    'PLI': ['Jaké jsou prediktivní biomarkery (PD-L1, EGFR, ALK, ROS1, KRAS)?',
            'Jaká je FEV1 a DLCO?',
            'Kdy byl poslední staging a co ukázal?',
            'Splňuje kritéria některé klinické studie?'],
    'PRS': ['Jaký je ER, PR, HER2 a Ki-67?',
            'Je známý stav BRCA nebo jiných zárodečných mutací?',
            'Co ukázalo poslední zobrazení prsu a stagingu?',
            'Jaká léčba už proběhla a s jakou odpovědí?'],
    'KRC': ['Jak se vyvíjí CEA?',
            'Jaký je stav RAS, BRAF a MSI?',
            'Popisuje radiolog jaterní ložiska jako resekabilní?',
            'Jaká léčba už proběhla a kdy?'],
    'OBC': ['Jaká je histologie a TNM?',
            'Jaký je ECOG a hlavní komorbidity?',
            'Co ukázalo poslední zobrazení?',
            'Které údaje pro rozhodnutí v dokumentaci chybí?'],
}
GENERAL = ['Co doporučují guidelines u metastatického onemocnění?',
           'Které studie jsou otevřené a pro jaké diagnózy?',
           'Jaká jsou kritéria resekability jaterních metastáz?']


def suggestions_for(icd10_codes: list[str] | None) -> dict:
    """`{area, questions}`; bez pacienta (dotaz jen na guidelines a studie) `area = None`."""
    if not icd10_codes:
        return {'area': None, 'questions': list(GENERAL)}
    from services.rules.fact_categories import area_for_icd10

    area = area_for_icd10(icd10_codes)
    return {'area': area, 'questions': list(SUGGESTIONS.get(area, SUGGESTIONS['OBC']))}
