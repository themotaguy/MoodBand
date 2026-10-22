// Step 2 of an intervention (decisions.md #13): the break itself, played with the
// phone in hand once the user has opened the suggestion. It first asks for the
// user's go-ahead (decisions.md #14), then plays the catalog's channels for the
// user's profile, and ends with "Was this right?". The on-demand break
// (`start=now`) and the recovery cue skip the question.
import { setAudioModeAsync } from 'expo-audio';
import { router, useLocalSearchParams } from 'expo-router';
import * as Speech from 'expo-speech';
import { useEffect, useState } from 'react';
import { AccessibilityInfo, Animated, AppState, Easing, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, text } from '@/components/Button';
import { CONFIRMATION, type Resolved, type Visual, isIntervention, resolve } from '@/catalog';
import { durationMs, play, playFrom, stop } from '@/haptics';
import { useAppState } from '@/state';

const MIN_SESSION_MS = 8000; // taps and cues are short; keep the screen up long enough to read
const INHALE_MS = 4000;
const CYCLE_MS = 10000;

const announce = (msg: string) => AccessibilityInfo.announceForAccessibilityWithOptions(msg, { queue: true });

// With VoiceOver on, its own reading of the screen and the app's speech would talk
// over each other, so spoken guidance is handed to VoiceOver, which queues it.
async function say(textToSay: string) {
  if (await AccessibilityInfo.isScreenReaderEnabled()) announce(textToSay);
  else Speech.speak(textToSay, { rate: 0.9 });
}

function startAudio(r: Resolved) {
  const audio = r.audio;
  if (!audio) return;
  if (audio.type === 'tts') say(audio.script);
  // Stand-ins until audio assets exist: no music files or chime yet.
  else if (audio.type === 'music') say('Music would start here.');
  else say(r.prompt);
}

function BreathingCircle({ visual, reduceMotion }: { visual: Visual; reduceMotion: boolean }) {
  const [scale] = useState(() => new Animated.Value(0.6));
  const [phase, setPhase] = useState<'in' | 'out'>('in');

  useEffect(() => {
    const start = Date.now();
    const tick = setInterval(() => setPhase((Date.now() - start) % CYCLE_MS < INHALE_MS ? 'in' : 'out'), 250);
    if (reduceMotion) return () => clearInterval(tick);
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(scale, { toValue: 1, duration: INHALE_MS, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      Animated.timing(scale, { toValue: 0.6, duration: CYCLE_MS - INHALE_MS, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
    ]));
    loop.start();
    return () => { clearInterval(tick); loop.stop(); };
  }, [reduceMotion, scale]);

  return (
    <View accessible accessibilityLabel={visual.screen_reader_text}>
      <View style={[styles.stage, visual.background ? { backgroundColor: visual.background } : null]}>
        <Animated.View style={[styles.circle, { backgroundColor: visual.colour, transform: [{ scale }] }]} />
      </View>
      {/* Below the circle, in black, so it stays readable on every profile's colours. */}
      <Text style={styles.phase}>{phase === 'in' ? 'Breathe in' : 'Breathe out'}</Text>
    </View>
  );
}

function ColourPanel({ visual, sessionMs }: { visual: Visual; sessionMs: number }) {
  const [fade] = useState(() => new Animated.Value(0));
  useEffect(() => {
    Animated.timing(fade, { toValue: 1, duration: sessionMs, useNativeDriver: false }).start();
  }, [fade, sessionMs]);
  const from = visual.colour_from ?? visual.colour ?? '#FFFFFF';
  const backgroundColor = fade.interpolate({ inputRange: [0, 1], outputRange: [from, visual.colour_to ?? from] });
  return (
    <Animated.View accessible accessibilityLabel={visual.screen_reader_text} style={[styles.stage, { backgroundColor }]}>
      <Text style={[styles.phase, styles.onColour]}>{visual.screen_reader_text}</Text>
    </Animated.View>
  );
}

export default function Session() {
  const { id, start } = useLocalSearchParams<{ id: string; start?: string }>();
  const { profile, recordAnswer } = useAppState();
  // The recovery cue is a message, not an exercise, so there is nothing to agree to.
  const skipAsk = start === 'now' || id === 'recovery_cue';
  const [phase, setPhase] = useState<'ask' | 'running' | 'done'>(skipAsk ? 'running' : 'ask');
  const [reduceMotion, setReduceMotion] = useState(false);
  const r = isIntervention(id) ? resolve(id, profile) : null;
  const sessionMs = r ? Math.max(durationMs(r.haptic), MIN_SESSION_MS) : 0;

  useEffect(() => {
    if (!r || phase !== 'running') return;
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    // The user agreed to this break, so play speech even on silent.
    setAudioModeAsync({ playsInSilentMode: true }).finally(() => startAudio(r));
    play(r.haptic);
    const startedAt = Date.now();
    const timer = setTimeout(() => setPhase('done'), sessionMs);
    // iOS stops the haptics while the app is inactive (e.g. Notification Center open);
    // when the user comes back, pick up where the break is now so the vibration stays in
    // step with the breathing circle. Only after a real interruption: opening the app from
    // a notification also reports "active", and restarting then would cut the start.
    let interrupted = false;
    const resume = AppState.addEventListener('change', s => {
      if (s !== 'active') interrupted = true;
      else if (interrupted && Date.now() - startedAt < sessionMs) {
        interrupted = false;
        playFrom(r.haptic, Date.now() - startedAt);
      }
    });
    return () => { clearTimeout(timer); resume.remove(); stop(); Speech.stop(); };
    // Runs once when the break starts; the profile can't change while this screen is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, phase === 'running']);

  useEffect(() => {
    if (phase === 'done') announce(CONFIRMATION.question);
  }, [phase]);

  if (!r) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={text.body}>Unknown break.</Text>
        <Button title="Back" onPress={() => router.back()} />
      </SafeAreaView>
    );
  }

  function finish() {
    stop();
    Speech.stop();
    setPhase('done');
  }

  function answer(a: 'yes' | 'no' | 'snooze' | 'not_now') {
    recordAnswer(r!.id, a);
    announce(a === 'not_now' ? 'Okay, maybe later.' : 'Thanks.');
    router.back();
  }

  const showVisual = !!r.visual;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text accessibilityRole="header" style={text.title}>{r.prompt}</Text>
        {phase === 'ask' ? (
          <>
            <Text style={text.body}>About {Math.round(sessionMs / 1000)} seconds. Nothing starts until you choose.</Text>
            <Button title="Start" hint="Starts the break." onPress={() => setPhase('running')} />
            <Button title="Not now" hint="Closes this suggestion." onPress={() => answer('not_now')} />
          </>
        ) : phase === 'running' ? (
          <>
            {showVisual && r.visual!.animation === 'breathing_circle' ? (
              <BreathingCircle visual={r.visual!} reduceMotion={reduceMotion} />
            ) : showVisual ? (
              <ColourPanel visual={r.visual!} sessionMs={sessionMs} />
            ) : null}
            <Text style={text.body}>About {Math.round(sessionMs / 1000)} seconds. Follow the vibration.</Text>
            <Button title="Stop" tone="danger" onPress={finish} />
          </>
        ) : (
          <>
            <Text accessibilityRole="header" style={text.section}>{CONFIRMATION.question}</Text>
            <Button title="Yes" hint="This break suited how I felt." onPress={() => answer('yes')} />
            <Button title="No" hint="I wasn't feeling like this." onPress={() => answer('no')} />
            <Button title="Snooze" hint="No suggestions for an hour." onPress={() => answer('snooze')} />
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  content: { padding: 20, gap: 16 },
  stage: { height: 320, borderRadius: 16, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  circle: { position: 'absolute', width: 260, height: 260, borderRadius: 130, opacity: 0.85 },
  phase: { fontSize: 32, fontWeight: '700', color: '#000000', textAlign: 'center', marginTop: 12 },
  onColour: { color: '#FFFFFF', marginTop: 0, paddingHorizontal: 16 },
});
