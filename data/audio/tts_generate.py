#!/usr/bin/env python3
"""Záložní nahrávka simulované diskuse MDT ze scénáře (T-314). Jen macOS: ``say`` + ``afconvert``, jinak stdlib.

    python3 data/audio/tts_generate.py data/audio/P03_mdt02_script.json

Vytvoří vedle scénáře:
- ``P03_mdt02.m4a``: audio (AAC), mluvčí se střídají hlasy z ``voices``;
- ``P03_mdt02_transcript.json``: referenční přepis ve schématu ``Transcript`` (services/ai_service.py),
  časy ``MM:SS`` spočítané ze skutečné délky úseků;
- ``P03_mdt02.md``: čitelný přepis (podle něj jde diskusi nahrát i lidmi, což je lepší než TTS).
"""
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

PAUSE_S = 0.5
SAMPLE_RATE = 22050


def _render(text: str, voice: str, rate: int, out: Path) -> None:
    subprocess.run(
        ['say', '-v', voice, '-r', str(rate), '--file-format=WAVE', f'--data-format=LEI16@{SAMPLE_RATE}',
         '-o', str(out), text],
        check=True,
    )


def _mmss(seconds: float) -> str:
    seconds = int(seconds)
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


def main(script_path: str) -> None:
    script_file = Path(script_path).resolve()
    script = json.loads(script_file.read_text(encoding='utf-8'))
    stem = script_file.name.replace('_script.json', '')
    out_dir = script_file.parent
    segments_out = []
    with tempfile.TemporaryDirectory() as tmp:
        wav_out = Path(tmp) / f'{stem}.wav'
        with wave.open(str(wav_out), 'wb') as combined:
            combined.setnchannels(1)
            combined.setsampwidth(2)
            combined.setframerate(SAMPLE_RATE)
            silence = b'\x00\x00' * int(PAUSE_S * SAMPLE_RATE)
            position = 0.0
            for i, seg in enumerate(script['segments']):
                voice = script['voices'][seg['speaker']]
                part = Path(tmp) / f'{i:02d}.wav'
                _render(seg['text'], voice['voice'], voice['rate'], part)
                with wave.open(str(part), 'rb') as w:
                    assert w.getframerate() == SAMPLE_RATE and w.getsampwidth() == 2 and w.getnchannels() == 1
                    frames = w.readframes(w.getnframes())
                    duration = w.getnframes() / SAMPLE_RATE
                segments_out.append({'speaker': seg['speaker'], 'start': _mmss(position), 'text': seg['text']})
                combined.writeframes(frames + silence)
                position += duration + PAUSE_S
        m4a = out_dir / f'{stem}.m4a'
        subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '48000', str(wav_out), str(m4a)], check=True)

    (out_dir / f'{stem}_transcript.json').write_text(
        json.dumps({'segments': segments_out}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    lines = [f"# Simulovaná diskuse MDT – {script['patient_id']} ({script['mdt_date']})", '',
             f"Referenční přepis k `{stem}.m4a` (T-314, BON-3). Délka {_mmss(position)}. "
             f"Uloží se jako `DocumentReference/{script['document_id']}`.", '']
    lines += [f"**{s['start']} · {s['speaker']}:** {s['text']}" + '\n' for s in segments_out]
    (out_dir / f'{stem}.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'{m4a.name}: {_mmss(position)}, {len(segments_out)} úseků')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / 'P03_mdt02_script.json'))
