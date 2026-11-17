import { describe, expect, it } from 'vitest';
import { parseVoiceCommand } from './voice';

describe('parseVoiceCommand (T-380)', () => {
  it.each([
    ['další pacient', { kind: 'case', delta: 1 }],
    ['Předchozí pacient.', { kind: 'case', delta: -1 }],
    ['dál', { kind: 'slide', delta: 1 }],
    ['další', { kind: 'slide', delta: 1 }],
    ['zpět', { kind: 'slide', delta: -1 }],
    ['pacient P05', { kind: 'patient', patientId: 'P05' }],
    ['pé nula pět', { kind: 'patient', patientId: 'P05' }],
    ['p 13', { kind: 'patient', patientId: 'P13' }],
    ['pacient 7', { kind: 'patient', patientId: 'P07' }],
    ['P120', { kind: 'patient', patientId: 'P120' }],
    ['projednáno', { kind: 'discussed' }],
    ['ukaž QR', { kind: 'qr' }],
  ])('%s', (text, expected) => {
    expect(parseVoiceCommand(text)).toEqual(expected);
  });

  it('ignores ordinary speech', () => {
    expect(parseVoiceCommand('pacientka má progresi v játrech')).toBeNull();
    expect(parseVoiceCommand('')).toBeNull();
  });
});
