// Turns the feedback catalog's haptic patterns (../feedback/interventions.json)
// into react-native-haptic-feedback events. Each catalog segment is
// {ms, amplitude 0-255, type?}: a non-zero segment becomes one Core Haptics
// continuous event (iOS) / waveform step (Android) lasting `ms`, or a single
// crisp tap at its start when type is "transient"; a zero segment is a gap.
import RNHapticFeedback, { type HapticEvent } from 'react-native-haptic-feedback';

import catalog from '../../feedback/interventions.json';

export type Segment = { ms: number; amplitude: number; type?: 'transient' };
export type HapticPattern = { description: string; segments: Segment[]; repeat: number };

export const patterns = catalog.haptic_patterns as Record<string, HapticPattern>;

const SHARPNESS = 0.3; // soft, rounded feel for continuous vibration
const TAP_SHARPNESS = 0.8; // crisp, so a transient reads as a tap, not a buzz

export function toEvents(pattern: HapticPattern): HapticEvent[] {
  const events: HapticEvent[] = [];
  let time = 0;
  for (let i = 0; i < pattern.repeat; i++) {
    for (const { ms, amplitude, type } of pattern.segments) {
      if (amplitude > 0 && type === 'transient') {
        events.push({ time, type: 'transient', intensity: amplitude / 255, sharpness: TAP_SHARPNESS });
      } else if (amplitude > 0) {
        events.push({ time, type: 'continuous', duration: ms, intensity: amplitude / 255, sharpness: SHARPNESS });
      }
      time += ms;
    }
  }
  return events;
}

export function durationMs(pattern: HapticPattern): number {
  return pattern.repeat * pattern.segments.reduce((sum, s) => sum + s.ms, 0);
}

export function play(pattern: HapticPattern) {
  RNHapticFeedback.stop(); // never layer a new pattern on top of one still playing
  RNHapticFeedback.triggerPattern(toEvents(pattern));
}

export function stop() {
  RNHapticFeedback.stop();
}

export const isSupported = () => RNHapticFeedback.isSupported();

// Prototype check: can the user feel the difference between weak and strong
// continuous vibration? The breathing pacer depends on it.
export const intensityCheck: HapticPattern = {
  description: 'Two seconds weak, a one-second pause, then two seconds strong.',
  segments: [{ ms: 2000, amplitude: 100 }, { ms: 1000, amplitude: 0 }, { ms: 2000, amplitude: 255 }],
  repeat: 1,
};
