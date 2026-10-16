"""Testy textů a odstavců (services.ai.text) a pseudonymizace (T-105)."""
import pytest

from services.ai.pseudonymize import Pseudonymizer, pseudonymize_text
from services.ai.text import resource_paragraphs, resource_text, split_paragraphs, strip_xhtml
from services.tests.dataset import load_patient

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]


class TestParagraphs:
    def test_blank_lines_and_headers(self):
        text = "Úvodní věta.\nPokračování.\n\nJátra: ložiska\n- S7: 29 mm\nZávěr: PR"
        paragraphs = split_paragraphs(text)
        assert [p.text for p in paragraphs] == [
            "Úvodní věta.\nPokračování.", "Játra: ložiska\n- S7: 29 mm", "Závěr: PR"]
        assert [p.index for p in paragraphs] == [1, 2, 3]

    def test_offsets_point_into_text(self):
        text = "  A\r\n\r\n  Závěr: B  \n"
        for p in split_paragraphs(text):
            assert text[p.start:p.end] == p.text
        assert [p.text for p in split_paragraphs(text)] == ["A", "Závěr: B"]

    def test_empty(self):
        assert split_paragraphs("") == [] and split_paragraphs(None) == []

    def test_p03_img03(self):
        report = next(r for r in load_patient("P03") if r["id"] == "P03-img03")
        paragraphs = resource_paragraphs(report)
        assert len(paragraphs) == 4
        assert paragraphs[0].text.endswith("hrudník nebyl požadován.")
        assert paragraphs[3].text.startswith("Závěr: Parciální odpověď dle RECIST 1.1")

    @pytest.mark.parametrize("patient_id", PATIENTS)
    def test_dataset_offsets_and_coverage(self, patient_id):
        for resource in load_patient(patient_id):
            text = resource_text(resource)
            if text is None:
                continue
            paragraphs = split_paragraphs(text)
            assert paragraphs, resource["id"]
            for p in paragraphs:
                assert text[p.start:p.end] == p.text and p.text.strip()
            # žádný neprázdný řádek se neztratí
            covered = "\n".join(p.text for p in paragraphs)
            assert [line for line in text.splitlines() if line.strip()] == \
                [line for line in covered.splitlines() if line.strip()]


class TestResourceText:
    def test_strip_xhtml(self):
        div = '<div xmlns="http://www.w3.org/1999/xhtml">1. a<br/>2. b &amp; c</div>'
        assert strip_xhtml(div) == "1. a\n2. b & c"

    def test_composition_sections(self):
        record = next(r for r in load_patient("P03") if r["id"] == "P03-mdt01")
        paragraphs = resource_paragraphs(record)
        assert [p.text.split(":")[0] for p in paragraphs] == [
            "Projednaná otázka", "Klinické zhodnocení", "Léčebný záměr", "Doporučený postup",
            "Klinická studie", "Plánované re-MDT", "Závěr MDT"]
        assert "\n2. [Chirurgie]" in paragraphs[3].text

    def test_service_request_question_first(self):
        request = next(r for r in load_patient("P03") if r["id"] == "P03-zad01")
        paragraphs = resource_paragraphs(request)
        assert paragraphs[0].text.startswith("Otázka pro MDT: Jsou jaterní metastázy")
        assert len(paragraphs) == 5

    def test_lab_report_and_observation_have_no_text(self):
        resources = {r["id"]: r for r in load_patient("P03")}
        assert resource_text(resources["P03-lab06"]) is None
        assert resource_text(resources["P03-ecog03"]) is None


class TestPseudonymize:
    @staticmethod
    def _valid_rc():
        return next(f"780101{n:04d}" for n in range(1000, 10000) if int(f"780101{n:04d}") % 11 == 0)

    def test_replaces_pii(self):
        rc = self._valid_rc()
        text = (f"Jan Novák, nar. 12. 3. 1959, RČ 590312/1234 i {rc}, tel. +420 777 123 456, "
                "e-mail jan.novak@example.cz. Pacient Jan Novák souhlasí.")
        pseudo = Pseudonymizer()
        pseudo.add_name("Jan Novák", "P03")
        out = pseudo(text)
        assert out == ("P03, [datum narození], RČ [RČ] i [RČ], tel. [telefon], e-mail [e-mail]. "
                       "Pacient P03 souhlasí.")
        assert pseudo.replacements == 7

    def test_keeps_clinical_numbers(self):
        text = "Hb 121 g/l, TK 135/85, CEA 13,9 µg/l, Tr 168, 2026-10-21 14:00, cT3 N1 M1a, 1234567890"
        assert pseudonymize_text(text) == text

    def test_short_names_ignored(self):
        assert pseudonymize_text("Ivo přišel", {"Ivo": "P01"}) == "Ivo přišel"
