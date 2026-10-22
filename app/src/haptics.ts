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
// The library's stop() shuts its haptic engine down asynchronously; starting a new
// pattern immediately can be silenced when that shutdown completes. Wait this long.
const RESTART_DELAY_MS = 150;
let pending: ReturnType<typeof setTimeout> | undefined;
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
  playFrom(pattern, 0);
}

/** Play the rest of a pattern from `offsetMs` in. iOS stops custom haptics when the
 * app goes inactive (e.g. Notification Center), so sessions resume with this. */
export function playFrom(pattern: HapticPattern, offsetMs: number) {
  const events: HapticEvent[] = [];
  for (const e of toEvents(pattern)) {
    const end = e.time + (e.duration ?? 0);
    if (e.type === 'continuous' && e.time < offsetMs && end > offsetMs) {
      events.push({ ...e, time: 0, duration: end - offsetMs }); // cut the event in progress
    } else if (e.time >= offsetMs) {
      events.push({ ...e, time: e.time - offsetMs });
    }
  }
  stop(); // never layer a new pattern on top of one still playing
  if (events.length) pending = setTimeout(() => RNHapticFeedback.triggerPattern(events), RESTART_DELAY_MS);
}

export function stop() {
  clearTimeout(pending);
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
