'use client';

import * as React from 'react';

/**
 * Hlasové ovládání jednání komise (T-380): předseda řídí projektor hlasem, když má ruce u PACS nebo u papírů.
 * Rozpoznání řeči dělá prohlížeč (Web Speech API, `cs-CZ`); do aplikace jde jen rozpoznaný text, žádný zvuk se
 * neukládá ani neposílá na náš server. Podporuje Chrome a Edge; jinde se tlačítko neukáže.
 */
export type VoiceCommand =
  | { kind: 'case'; delta: 1 | -1 }
  | { kind: 'slide'; delta: 1 | -1 }
  | { kind: 'patient'; patientId: string }
  | { kind: 'discussed' }
  | { kind: 'qr' };

const NUMBERS: Record<string, string> = {
  nula: '0', jedna: '1', jedno: '1', jeden: '1', dva: '2', dvě: '2', tři: '3', čtyři: '4', pět: '5', šest: '6',
  sedm: '7', osm: '8', devět: '9',
};

/** Celé slovo i s diakritikou: `\b` v JS bere jako písmena jen ASCII („předchozí“ by nenašel). */
const word = (pattern: string) => new RegExp(`(?<![\\p{L}\\d])(?:${pattern})(?![\\p{L}\\d])`, 'u');

const PATIENT_CODE = /(?<![\p{L}\d])(?:pacient(?:a|ka|ku)?\s+)?(?:p|pé|pe)\s*((?:\d\s*){1,3})(?![\p{L}\d])/u;
const PATIENT_NUMBER = /(?<![\p{L}\d])pacient(?:a|ka|ku)?\s+((?:\d\s*){1,3})(?![\p{L}\d])/u;
const SPOKEN_DIGIT = /(?<![\p{L}\d])(nula|jedna|jedno|jeden|dvě|dva|tři|čtyři|pět|šest|sedm|osm|devět)(?![\p{L}\d])/gu;
const QR = word('qr|kód pro příchod|kod pro prichod');
const DISCUSSED = word('projednán[oa]?|projednan[oa]?|hotovo');
const BACK = word('předchozí|predchozi|zpět|zpet|minulý|minuly');
const FORWARD = word('další|dalsi|dál|dal|následující|nasledujici');
const PATIENT_WORD = word('pacient(?:a|ka|ku|ovi)?');

/** Text z rozpoznání řeči → příkaz (nebo `null`, když nic nesedí). Bez diakritiky i s ní, malými i velkými. */
export function parseVoiceCommand(raw: string): VoiceCommand | null {
  const text = raw.toLowerCase().replace(/[.,!?]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!text) return null;
  // „pacient P05“, „pé nula pět“, „p 5“, „pacient 13“
  const spoken = text.replace(SPOKEN_DIGIT, (w) => NUMBERS[w]);
  const patient = spoken.match(PATIENT_CODE) ?? spoken.match(PATIENT_NUMBER);
  if (patient) {
    const digits = patient[1].replace(/\s/g, '');
    if (digits.length >= 1 && digits.length <= 3) return { kind: 'patient', patientId: `P${digits.padStart(2, '0')}` };
  }
  if (QR.test(text)) return { kind: 'qr' };
  if (DISCUSSED.test(text)) return { kind: 'discussed' };
  const back = BACK.test(text);
  const forward = FORWARD.test(text);
  if (PATIENT_WORD.test(text) && (back || forward)) return { kind: 'case', delta: back ? -1 : 1 };
  if (back) return { kind: 'slide', delta: -1 };
  if (forward) return { kind: 'slide', delta: 1 };
  return null;
}

type Recognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  start: () => void;
  stop: () => void;
};

function recognitionClass(): (new () => Recognition) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export const voiceSupported = () => recognitionClass() !== null;

/**
 * Zapnuté hlasové ovládání: poslouchá, dokud ho předseda nevypne (prohlížeč po tichu poslech ukončí, proto se
 * sám znovu spustí). `onCommand` dostane rozpoznaný příkaz, `onHeard` text (pro „rozumím: …“ v UI).
 */
export function useVoiceControl(
  active: boolean,
  onCommand: (command: VoiceCommand, heard: string) => void,
  onError?: (message: string) => void,
) {
  const handler = React.useRef(onCommand);
  const errorHandler = React.useRef(onError);
  React.useEffect(() => {
    handler.current = onCommand;
    errorHandler.current = onError;
  });
  React.useEffect(() => {
    const Ctor = recognitionClass();
    if (!active || !Ctor) return;
    let stopped = false;
    const recognition = new Ctor();
    recognition.lang = 'cs-CZ';
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (!result.isFinal) continue;
        const heard = result[0]?.transcript ?? '';
        const command = parseVoiceCommand(heard);
        if (command) handler.current(command, heard);
      }
    };
    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        stopped = true;
        errorHandler.current?.('Prohlížeč nepovolil mikrofon. Povolte ho v nastavení stránky.');
      }
    };
    recognition.onend = () => {
      if (!stopped) recognition.start();             // po tichu prohlížeč poslech ukončí: pokračovat
    };
    recognition.start();
    return () => {
      stopped = true;
      recognition.onend = null;
      recognition.stop();
    };
  }, [active]);
}
