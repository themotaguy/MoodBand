// Replay mode (decisions.md #18): a recorded LifeSnaps day, run through the model and
// the decision module on the laptop (feedback/server.py), played back on the phone in
// compressed time. Suggestions are scheduled as local notifications in advance, so they
// arrive with the phone locked and need no push entitlement.
import type { Answer } from './state';

export const SIM_MINUTES_PER_SECOND = 1; // 1 hour of the day plays in 1 minute

export type Mood = 'happy' | 'neutral' | 'sad' | 'stressed';

export type Day = { id: string; date: string; suggestions: number; matched: number; reports: number };

export type Step = {
  time: string;
  minute: number;                        // minutes since midnight
  probabilities: Record<Mood, number>;
  predicted: Mood;
  reason: string;                        // decision module's reason (intervene, cooldown, ...)
  mood: string | null;
  intervention: string | null;
  reported: string | null;               // the person's report within 30 min, when one fired
};

export type Timeline = { id: string; date: string; steps: Step[]; reports: { time: string; minute: number; mood: string }[] };

export const shortId = (id: string) => id.slice(-4);

export function formatDay(day: Pick<Day, 'id' | 'date'>) {
  const date = new Date(`${day.date}T12:00:00`).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  return `${date}, participant ${shortId(day.id)}`;
}

/** Real time at which a minute of the recorded day plays, for a replay started at `startedAt`. */
export function playsAt(timeline: Timeline, minute: number, startedAt: number) {
  return new Date(startedAt + ((minute - timeline.steps[0].minute) / SIM_MINUTES_PER_SECOND) * 1000);
}

/** Minute of the recorded day being played now (clamped to the day). */
export function simMinute(timeline: Timeline, startedAt: number, now = Date.now()) {
  const first = timeline.steps[0].minute;
  const last = timeline.steps[timeline.steps.length - 1].minute;
  return Math.min(last, first + Math.floor(((now - startedAt) / 1000) * SIM_MINUTES_PER_SECOND));
}

export const clock = (minute: number) =>
  `${String(Math.floor(minute / 60)).padStart(2, '0')}:${String(minute % 60).padStart(2, '0')}`;

async function request<T>(server: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${server.replace(/\/+$/, '')}${path}`, init);
  if (!res.ok) throw new Error(`Server replied ${res.status}`);
  return res.json() as Promise<T>;
}

export const fetchDays = (server: string) => request<Day[]>(server, '/days');

export const fetchTimeline = (server: string, day: Pick<Day, 'id' | 'date'>) =>
  request<Timeline>(server, `/replay?id=${encodeURIComponent(day.id)}&date=${encodeURIComponent(day.date)}`);

/** Send one replay answer to the laptop, which adds the person's nearby report and saves it. */
export function postAnswer(server: string, a: Answer & { replay: NonNullable<Answer['replay']> }) {
  return request(server, '/answers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      answered_at: a.at,
      id: a.replay.participant,
      date: a.replay.date,
      time: a.replay.time,
      intervention: a.intervention,
      predicted_mood: a.replay.mood,
      answer: a.answer,
      profile: a.profile,
    }),
  });
}
