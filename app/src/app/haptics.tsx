// Haptics test: plays every vibration pattern in the feedback catalog on the
// phone, to check they can be felt and told apart (decisions.md #12,
// Docs/haptics-prototype-test.md). Fully usable with VoiceOver.
import { useEffect } from 'react';
import { AccessibilityInfo, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { type HapticPattern, durationMs, intensityCheck, isSupported, patterns, play, stop } from '@/haptics';

const LABELS: Record<string, string> = {
  breathing_pacer: 'Breathing pacer',
  slow_heartbeat: 'Slow heartbeat',
  descending_pulses: 'Descending pulses',
  soft_tap: 'Soft tap',
  double_tap: 'Double tap',
};

function PatternButton({ label, pattern }: { label: string; pattern: HapticPattern }) {
  const seconds = Math.round(durationMs(pattern) / 1000);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${label}, ${seconds} seconds`}
      accessibilityHint={pattern.description}
      onPress={() => {
        play(pattern);
        // VoiceOver re-reads the button on activation, so the queued announcement
        // only adds what's new.
        AccessibilityInfo.announceForAccessibilityWithOptions('Playing', { queue: true });
      }}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
    >
      <Text style={styles.buttonText}>{label}</Text>
      <Text style={styles.detail}>{seconds} s · {pattern.description}</Text>
    </Pressable>
  );
}

export default function HapticsTest() {
  const supported = isSupported();
  useEffect(() => stop, []);

  return (
    <ScrollView contentContainerStyle={styles.content} contentInsetAdjustmentBehavior="automatic">
      <Text style={styles.status}>
        {supported ? 'Custom haptics supported on this phone.' : 'This phone does not support custom haptics.'}
      </Text>

      <Text accessibilityRole="header" style={styles.section}>1. Intensity check</Text>
      <PatternButton label="Weak then strong" pattern={intensityCheck} />

      <Text accessibilityRole="header" style={styles.section}>2. Catalog patterns</Text>
      {Object.entries(patterns).map(([key, pattern]) => (
        <PatternButton key={key} label={LABELS[key] ?? key} pattern={pattern} />
      ))}

      <View style={styles.spacer} />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Stop vibration"
        onPress={() => {
          stop();
          AccessibilityInfo.announceForAccessibilityWithOptions('Stopped', { queue: true });
        }}
        style={({ pressed }) => [styles.button, styles.stop, pressed && styles.pressed]}
      >
        <Text style={[styles.buttonText, styles.stopText]}>Stop</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 12 },
  status: { fontSize: 17, color: '#1A1A1A' },
  section: { fontSize: 20, fontWeight: '600', color: '#000000', marginTop: 12 },
  button: {
    minHeight: 64,
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#0B3D91',
    backgroundColor: '#E8EEF9',
    justifyContent: 'center',
  },
  pressed: { backgroundColor: '#C9D7F0' },
  buttonText: { fontSize: 20, fontWeight: '600', color: '#0B3D91' },
  detail: { fontSize: 15, color: '#1A1A1A', marginTop: 4 },
  spacer: { height: 8 },
  stop: { borderColor: '#8A1C1C', backgroundColor: '#FBE9E9' },
  stopText: { color: '#8A1C1C' },
});
