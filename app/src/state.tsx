// App-wide prototype state: the user's accessibility profile, snooze, and the
// "Was this right?" answers. In memory only for now (lost on reload); answers
// will later be stored and used as personal labels (decisions.md #11).
import { createContext, type ReactNode, useContext, useMemo, useState } from 'react';

import type { Profile } from './catalog';

export type Answer = { intervention: string; answer: 'yes' | 'no' | 'snooze' | 'not_now'; at: Date };

type State = {
  profile: Profile;
  setProfile: (p: Profile) => void;
  snoozedUntil: Date | null;
  answers: Answer[];
  recordAnswer: (intervention: string, answer: Answer['answer']) => void;
};

const SNOOZE_MS = 60 * 60 * 1000;

const StateContext = createContext<State | null>(null);

export function StateProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile>('sighted');
  const [snoozedUntil, setSnoozedUntil] = useState<Date | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);

  const value = useMemo<State>(() => ({
    profile,
    setProfile,
    snoozedUntil,
    answers,
    recordAnswer: (intervention, answer) => {
      setAnswers(a => [{ intervention, answer, at: new Date() }, ...a]);
      if (answer === 'snooze') setSnoozedUntil(new Date(Date.now() + SNOOZE_MS));
    },
  }), [profile, snoozedUntil, answers]);

  return <StateContext.Provider value={value}>{children}</StateContext.Provider>;
}

export function useAppState(): State {
  const state = useContext(StateContext);
  if (!state) throw new Error('useAppState must be used inside StateProvider');
  return state;
}
