// Reads interventions from the shared feedback catalog (../feedback/interventions.json)
// and resolves which channels a user gets for their accessibility profile.
// Mirrors FeedbackDecider._resolve in feedback/decision.py; the catalog itself is
// validated against the accessibility rules by that module's tests.
import catalog from '../../feedback/interventions.json';

import { type HapticPattern, patterns } from './haptics';

export type Profile = 'sighted' | 'low_vision' | 'blind';
export const PROFILES: { id: Profile; label: string }[] = [
  { id: 'sighted', label: 'Sighted' },
  { id: 'low_vision', label: 'Low vision' },
  { id: 'blind', label: 'Blind or visually impaired' },
];

export type Audio =
  | { type: 'tts'; script: string }
  | { type: 'music'; playlist: string; description: string }
  | { type: 'sound'; asset: string };

export type Visual = {
  colour?: string;
  colour_from?: string;
  colour_to?: string;
  background?: string;
  animation: string;
  high_contrast: boolean;
  optional?: boolean;
  screen_reader_text: string;
};

export type Channels = { haptic: string; audio?: Audio; visual?: Visual };

type Entry = { prompt: string; profiles: Record<Profile, Channels> };
const interventions = catalog.interventions as unknown as Record<string, Entry>;

export type Resolved = {
  id: string;
  prompt: string;
  haptic: HapticPattern;
  audio?: Audio;
  visual?: Visual;
};

export const MOOD_TO_INTERVENTION = catalog.moods as Record<string, string>;
export const ON_DEMAND = catalog.on_demand;
export const CONFIRMATION = catalog.confirmation;

export function isIntervention(id: string): boolean {
  return id in interventions;
}

export function resolve(id: string, profile: Profile): Resolved {
  const entry = interventions[id];
  const channels = entry.profiles[profile];
  return {
    id,
    prompt: entry.prompt,
    haptic: patterns[channels.haptic],
    audio: channels.audio,
    visual: channels.visual,
  };
}
