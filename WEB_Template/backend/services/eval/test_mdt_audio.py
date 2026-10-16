"""Simulovaná diskuse MDT k P03 (T-314, BON-3): nahrávka, referenční přepis a očekávaný závěr pro AI zapisovatele."""
import json
import re
from datetime import date
from pathlib import Path

import pytest

from services.ai_service import Transcript


def _audio_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'data' / 'audio' / 'P03_mdt02_script.json').is_file():
            return parent / 'data' / 'audio'
    pytest.skip('data/audio s nahrávkou P03 není k dispozici')


def test_reference_transcript_matches_schema_and_script():
    audio = _audio_dir()
    script = json.loads((audio / 'P03_mdt02_script.json').read_text(encoding='utf-8'))
    transcript = Transcript.model_validate_json((audio / 'P03_mdt02_transcript.json').read_text(encoding='utf-8'))
    assert [(s.speaker, s.text) for s in transcript.segments] == [(s['speaker'], s['text']) for s in script['segments']]
    starts = [s.start for s in transcript.segments]
    assert all(re.fullmatch(r'\d{2}:\d{2}', s) for s in starts) and starts == sorted(starts)
    assert '02:00' <= starts[-1] <= '03:10'                          # 2–3 minuty
    assert {s.speaker for s in transcript.segments} >= {'předseda', 'onkolog', 'chirurg', 'radiolog', 'patolog'}
    m4a = audio / 'P03_mdt02.m4a'
    assert m4a.is_file() and m4a.stat().st_size < 20 * 1024 * 1024   # inline audio do Gemini ≤ 20 MB (ARCH §5.6)


def test_expected_decision_is_in_transcript():
    """Závěr, který má AI zapisovatel z nahrávky vytáhnout, v diskusi opravdu zazní (nic nedomýšlí)."""
    audio = _audio_dir()
    script = json.loads((audio / 'P03_mdt02_script.json').read_text(encoding='utf-8'))
    decision = script['expected_decision']
    spoken = ' '.join(s['text'] for s in script['segments']).lower()
    assert decision['intent'] == 'kurativni' and 'kurativní' in spoken
    assert 'čtvrtého listopadu' in spoken and decision['re_mdt'] == '2026-11-04'
    for task in decision['tasks']:
        assert task['owner'] in spoken
        if task['due_date']:
            assert date.fromisoformat(task['due_date']).weekday() < 5          # pracovní den
    assert date.fromisoformat(decision['re_mdt']).weekday() == date(2026, 10, 21).weekday()   # stejný den v týdnu jako MDT
