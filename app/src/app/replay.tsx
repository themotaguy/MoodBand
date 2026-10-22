// Replay a recorded day (decisions.md #18): pick a LifeSnaps day from the laptop
// server, then play it at one hour per minute. Each suggestion the decision module
// made is scheduled as a notification; tapping it opens the usual session.
import { useEffect, useState } from 'react';
import { AccessibilityInfo, Alert, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button, text } from '@/components/Button';
import { resolve } from '@/catalog';
import { cancelSuggestion, ensurePermission, scheduleReplaySuggestion } from '@/notifications';
import {
  type Day, type Timeline, clock, fetchDays, fetchTimeline, formatDay, playsAt, simMinute,
} from '@/replay';
import { useAppState } from '@/state';

const REASONS: Record<string, string> = {
  intervene: 'Suggested a break',
  recovery: 'Sent the recovery cue',
  low_confidence: 'Not confident enough to act',
  not_persistent: 'Waiting to see if it lasts',
  positive_state: 'Positive mood, nothing to do',
  exercise: 'Ignored: just after activity',
  cooldown: 'Too soon after the last suggestion',
  daily_cap: 'Daily limit reached',
  quiet_hours: 'Quiet hours',
  snoozed: 'Snoozed',
};

const announce = (msg: string) => AccessibilityInfo.announceForAccessibilityWithOptions(msg, { queue: true });

export default function Replay() {
  const { profile, server, setServer, replayRun, setReplayRun } = useAppState();
  const [days, setDays] = useState<Day[] | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(replayRun?.timeline ?? null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!replayRun) return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, [replayRun]);

  async function call<T>(work: () => Promise<T>): Promise<T | null> {
    setError(null);
    try {
      return await work();
    } catch {
      const msg = 'Could not reach the laptop. Check the address, that the server is running, and that both are on the same Wi-Fi.';
      setError(msg);
      announce(msg);
      return null;
    }
  }

  async function loadDays() {
    const d = await call(() => fetchDays(server));
    if (d) {
      setDays(d);
      announce(`${d.length} days loaded.`);
    }
  }

  async function pick(day: Day) {
    const t = await call(() => fetchTimeline(server, day));
    if (t) {
      setTimeline(t);
      announce(`${formatDay(t)} ready.`);
    }
  }

  async function start() {
    if (!timeline) return;
    if (!(await ensurePermission())) {
      Alert.alert('Notifications are off', 'Allow notifications for MoodBand in Settings to replay a day.');
      return;
    }
    const startedAt = Date.now();
    const scheduled: { id: string; at: number }[] = [];
    for (const s of timeline.steps) {
      if (!s.intervention) continue;
      const at = playsAt(timeline, s.minute, startedAt);
      if (at.getTime() <= Date.now()) continue;
      const id = await scheduleReplaySuggestion(s.intervention, resolve(s.intervention, profile).prompt, at,
        { participant: timeline.id, date: timeline.date, time: s.time, mood: s.mood ?? s.predicted },
        s.intervention === 'recovery_cue');
      scheduled.push({ id, at: at.getTime() });
    }
    setNow(startedAt);
    setReplayRun({ timeline, startedAt, scheduled });
    announce(`Replay started. ${scheduled.length} suggestions will arrive as notifications.`);
  }

  function stopReplay() {
    replayRun?.scheduled.forEach(s => cancelSuggestion(s.id));
    setReplayRun(null);
    announce('Replay stopped.');
  }

  const running = replayRun !== null;
  const t = replayRun?.timeline ?? timeline;
  const minute = replayRun ? simMinute(replayRun.timeline, replayRun.startedAt, now) : null;
  const finished = replayRun !== null && minute === t!.steps[t!.steps.length - 1].minute;
  const current = t && minute !== null ? [...t.steps].reverse().find(s => s.minute <= minute) : undefined;
  const fired = t ? t.steps.filter(s => s.intervention) : [];
  const pending = new Set(replayRun?.scheduled.filter(s => s.at > now).map(s => s.at));

  return (
    <ScrollView contentContainerStyle={styles.content} contentInsetAdjustmentBehavior="automatic">
      {!running ? (
        <>
          <Text style={text.body}>
            Plays a recorded day from the LifeSnaps study through the mood model and the decision module on the laptop,
            at one hour per minute. Suggestions arrive as notifications, just as they will with a live Fitbit.
          </Text>
          <Text accessibilityRole="header" style={text.section}>Laptop server</Text>
          <TextInput
            accessibilityLabel="Laptop server address"
            accessibilityHint="Shown when the server starts, for example http://192.168.1.20:8787"
            value={server}
            onChangeText={setServer}
            placeholder="http://192.168.1.20:8787"
            placeholderTextColor="#5A5A5A"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            style={styles.input}
          />
          <Button title="Load days" onPress={loadDays} />
          {error ? <Text accessibilityRole="alert" style={[text.body, styles.error]}>{error}</Text> : null}
          {days?.map(d => (
            <Button
              key={`${d.id}-${d.date}`}
              title={formatDay(d)}
              detail={`${d.suggestions} suggestions, ${d.matched} matched the person's own report`}
              role="radio"
              state={{ checked: timeline?.id === d.id && timeline?.date === d.date }}
              tone={timeline?.id === d.id && timeline?.date === d.date ? 'selected' : 'primary'}
              onPress={() => pick(d)}
            />
          ))}
          {timeline ? (
            <>
              <Text accessibilityRole="header" style={text.section}>{formatDay(timeline)}</Text>
              <Text style={text.body}>
                {fired.length} suggestions from {timeline.steps[0].time} to {timeline.steps[timeline.steps.length - 1].time}.
                The whole day takes about {Math.round(timeline.steps.length * 10 / 60)} minutes. Lock the phone if you like.
              </Text>
              <Button title="Start replay" hint="Plays the day at one hour per minute." onPress={start} />
            </>
          ) : null}
        </>
      ) : (
        <>
          <Text accessibilityRole="header" style={text.section}>{formatDay(t!)}</Text>
          <View
            accessible
            accessibilityLabel={`Recorded time ${clock(minute!)}. Model reads ${current?.predicted ?? 'nothing yet'}` +
              `${current ? `, ${Math.round(current.probabilities[current.predicted] * 100)} percent` : ''}. ` +
              `${current ? REASONS[current.reason] ?? current.reason : ''}.`}
            style={styles.now}
          >
            <Text style={styles.clock}>{clock(minute!)}</Text>
            {current ? (
              <>
                <Text style={text.body}>
                  Model reads <Text style={styles.strong}>{current.predicted}</Text>{' '}
                  ({Math.round(current.probabilities[current.predicted] * 100)}%)
                </Text>
                <Text style={text.body}>{REASONS[current.reason] ?? current.reason}</Text>
              </>
            ) : null}
          </View>
          {finished ? <Text style={text.body}>The day has finished.</Text> : null}
          <Button title={finished ? 'Done' : 'Stop replay'} tone={finished ? 'primary' : 'danger'} onPress={stopReplay} />

          <Text accessibilityRole="header" style={text.section}>Suggestions</Text>
          {fired.map(s => (
            <Text key={s.minute} style={text.body}>
              {s.time}: {s.intervention!.replace(/_/g, ' ')} for {s.mood}
              {pending.has(playsAt(t!, s.minute, replayRun!.startedAt).getTime()) ? ' (coming up)' : ''}
              {s.reported && s.minute <= minute! ? `. They reported ${s.reported}.` : ''}
            </Text>
          ))}

          <Text accessibilityRole="header" style={text.section}>What the person reported</Text>
          {t!.reports.filter(r => r.minute <= minute!).length === 0 ? (
            <Text style={text.body}>No reports yet today.</Text>
          ) : (
            t!.reports.filter(r => r.minute <= minute!).map(r => (
              <Text key={r.minute} style={text.body}>{r.time}: {r.mood}</Text>
            ))
          )}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 12 },
  input: {
    minHeight: 56, borderWidth: 2, borderColor: '#0B3D91', borderRadius: 12,
    paddingHorizontal: 16, fontSize: 17, color: '#000000', backgroundColor: '#FFFFFF',
  },
  error: { color: '#8A1C1C' },
  now: { padding: 16, borderRadius: 12, backgroundColor: '#F1F4FA', gap: 4 },
  clock: { fontSize: 44, fontWeight: '700', color: '#000000', fontVariant: ['tabular-nums'] },
  strong: { fontWeight: '700' },
});
