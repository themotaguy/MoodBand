// Home: accessibility profile, test notifications for each suggestion, the
// on-demand break, and the "Was this right?" answers so far.
import { router } from 'expo-router';
import { useEffect } from 'react';
import { AccessibilityInfo, Alert, ScrollView, StyleSheet, Text } from 'react-native';

import { Button, text } from '@/components/Button';
import { ON_DEMAND, PROFILES, isIntervention, resolve } from '@/catalog';
import { ensurePermission, onSuggestionOpened, scheduleSuggestion } from '@/notifications';
import { useAppState } from '@/state';

const TESTS = [
  { id: 'breathing_break', title: 'Stress suggestion' },
  { id: 'iso_music', title: 'Sadness suggestion' },
  { id: 'recovery_cue', title: 'Recovery cue (quiet)' },
];
const DELAY_S = 5;

const announce = (msg: string) => AccessibilityInfo.announceForAccessibilityWithOptions(msg, { queue: true });

export default function Home() {
  const { profile, setProfile, answers, snoozedUntil } = useAppState();

  // Tapping a suggestion notification opens its session (also from a cold start).
  useEffect(() => onSuggestionOpened(id => {
    if (isIntervention(id)) router.push({ pathname: '/session/[id]', params: { id } });
  }), []);

  async function sendTest(id: string) {
    if (!(await ensurePermission())) {
      Alert.alert('Notifications are off', 'Allow notifications for MoodBand in Settings to test suggestions.');
      return;
    }
    await scheduleSuggestion(id, resolve(id, profile).prompt, DELAY_S, id === 'recovery_cue');
    announce(`Scheduled. Arrives in ${DELAY_S} seconds.`);
  }

  return (
    <ScrollView contentContainerStyle={styles.content} contentInsetAdjustmentBehavior="automatic">
      <Text accessibilityRole="header" style={text.section}>Accessibility profile</Text>
      {PROFILES.map(p => (
        <Button
          key={p.id}
          title={p.label}
          role="radio"
          state={{ checked: profile === p.id }}
          tone={profile === p.id ? 'selected' : 'primary'}
          onPress={() => setProfile(p.id)}
        />
      ))}

      <Text accessibilityRole="header" style={text.section}>Test a suggestion</Text>
      <Text style={text.body}>
        Sends the notification in {DELAY_S} seconds. Lock your phone or go to the home screen, then tap the
        notification to start the break.
      </Text>
      {TESTS.map(t => (
        <Button key={t.id} title={t.title} detail={`“${resolve(t.id, profile).prompt}”`} onPress={() => sendTest(t.id)} />
      ))}
      {snoozedUntil && snoozedUntil > new Date() ? (
        <Text style={text.body}>
          Snoozed until {snoozedUntil.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}. Automatic
          suggestions would be paused; test buttons still work.
        </Text>
      ) : null}

      <Text accessibilityRole="header" style={text.section}>Right now</Text>
      <Button
        title="I need a break"
        hint="Starts a one-minute breathing break."
        onPress={() => router.push({ pathname: '/session/[id]', params: { id: ON_DEMAND, start: 'now' } })}
      />

      <Text accessibilityRole="header" style={text.section}>Your answers</Text>
      {answers.length === 0 ? (
        <Text style={text.body}>No answers yet. After each break you’ll be asked whether it was right.</Text>
      ) : (
        answers.map(a => (
          <Text key={a.at.toISOString()} style={text.body}>
            {a.at.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}: {a.intervention.replace('_', ' ')} — {a.answer.replace('_', ' ')}
          </Text>
        ))
      )}

      <Text accessibilityRole="header" style={text.section}>Developer</Text>
      <Button title="Haptics test" role="link" onPress={() => router.push('/haptics')} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 12 },
});
