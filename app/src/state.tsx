// App-wide state: the user's accessibility profile, snooze, the "Was this right?"
// answers, the replay server's address and the replay that is playing. Profile,
// server and answers are kept on the phone (AsyncStorage), so they survive restarts;
// replay answers are also sent to the laptop (feedback/server.py), retried until it
// accepts them. Answers are evaluation and personalization labels, never model inputs (decisions.md #20).
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, type ReactNode, useContext, useEffect, useMemo, useRef, useState } from 'react';

import type { Profile } from './catalog';
import { cancelSuggestion, type ReplayContext } from './notifications';
import { SIM_MINUTES_PER_SECOND, type Timeline, postAnswer } from './replay';

export type Answer = {
  intervention: string;
  answer: 'yes' | 'no' | 'snooze' | 'not_now';
  at: string;                  // ISO time the user answered
  profile: Profile;
  replay?: ReplayContext;      // set when the suggestion came from a replayed day
  sent?: boolean;              // replay answers: accepted by the laptop
};

export type ReplayRun = { timeline: Timeline; startedAt: number; scheduled: { id: string; at: number }[] };

type State = {
  profile: Profile;
  setProfile: (p: Profile) => void;
  snoozedUntil: Date | null;
  answers: Answer[];
  recordAnswer: (intervention: string, answer: Answer['answer'], replay?: ReplayContext) => void;
  server: string;
  setServer: (s: string) => void;
  replayRun: ReplayRun | null;
  setReplayRun: (r: ReplayRun | null) => void;
};

const SNOOZE_MS = 60 * 60 * 1000;
const KEY = { profile: 'moodband.profile', server: 'moodband.server', answers: 'moodband.answers' };

const StateContext = createContext<State | null>(null);

export function StateProvider({ children }: { children: ReactNode }) {
  const [loaded, setLoaded] = useState(false);
  const [profile, setProfile] = useState<Profile>('sighted');
  const [server, setServer] = useState('');
  const [snoozedUntil, setSnoozedUntil] = useState<Date | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [replayRun, setReplayRun] = useState<ReplayRun | null>(null);
  const sending = useRef(new Set<string>());

  useEffect(() => {
    AsyncStorage.multiGet(Object.values(KEY)).then(entries => {
      const v = Object.fromEntries(entries);
      if (v[KEY.profile]) setProfile(v[KEY.profile] as Profile);
      if (v[KEY.server]) setServer(v[KEY.server]!);
      if (v[KEY.answers]) setAnswers(JSON.parse(v[KEY.answers]!));
    }).catch(() => {}).finally(() => setLoaded(true));
  }, []);

  // Save after loading, so the empty starting state never overwrites what was stored.
  useEffect(() => {
    if (!loaded) return;
    AsyncStorage.multiSet([[KEY.profile, profile], [KEY.server, server], [KEY.answers, JSON.stringify(answers)]]);
  }, [loaded, profile, server, answers]);

  // Send replay answers the laptop hasn't accepted yet.
  useEffect(() => {
    if (!loaded || !server) return;
    for (const a of answers) {
      if (!a.replay || a.sent || sending.current.has(a.at)) continue;
      sending.current.add(a.at);
      postAnswer(server, { ...a, replay: a.replay })
        .then(() => setAnswers(all => all.map(x => (x.at === a.at ? { ...x, sent: true } : x))))
        .catch(() => {})
        .finally(() => sending.current.delete(a.at));
    }
  }, [loaded, server, answers]);

  const value = useMemo<State>(() => ({
    profile,
    setProfile,
    snoozedUntil,
    answers,
    recordAnswer: (intervention, answer, replay) => {
      setAnswers(a => [{ intervention, answer, at: new Date().toISOString(), profile, replay }, ...a]);
      if (answer !== 'snooze') return;
      if (!replay) {
        setSnoozedUntil(new Date(Date.now() + SNOOZE_MS));
      } else if (replayRun) {
        // In a replay, snooze skips the suggestions due in the next hour of the recorded day.
        const until = Date.now() + SNOOZE_MS / 60 / SIM_MINUTES_PER_SECOND;
        const skipped = replayRun.scheduled.filter(s => s.at <= until);
        skipped.forEach(s => cancelSuggestion(s.id));
        setReplayRun({ ...replayRun, scheduled: replayRun.scheduled.filter(s => s.at > until) });
      }
    },
    server,
    setServer,
    replayRun,
    setReplayRun,
  }), [profile, snoozedUntil, answers, server, replayRun]);

  return <StateContext.Provider value={value}>{children}</StateContext.Provider>;
}

export function useAppState(): State {
  const state = useContext(StateContext);
  if (!state) throw new Error('useAppState must be used inside StateProvider');
  return state;
}
