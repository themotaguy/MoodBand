// Large, high-contrast button with VoiceOver label/hint/state. Shared by all screens.
import { type AccessibilityState, Pressable, StyleSheet, Text } from 'react-native';

type Props = {
  title: string;
  detail?: string;
  onPress: () => void;
  label?: string;              // VoiceOver label if it should differ from the title
  hint?: string;
  role?: 'button' | 'radio' | 'link';
  state?: AccessibilityState;
  tone?: 'primary' | 'danger' | 'selected';
};

export function Button({ title, detail, onPress, label, hint, role = 'button', state, tone = 'primary' }: Props) {
  return (
    <Pressable
      accessibilityRole={role}
      accessibilityLabel={label ?? title}
      accessibilityHint={hint}
      accessibilityState={state}
      onPress={onPress}
      style={({ pressed }) => [styles.button, styles[tone], pressed && styles.pressed]}
    >
      <Text style={[styles.title, tone === 'danger' && styles.dangerText]}>{title}</Text>
      {detail ? <Text style={styles.detail}>{detail}</Text> : null}
    </Pressable>
  );
}

export const text = StyleSheet.create({
  title: { fontSize: 28, fontWeight: '700', color: '#000000' },
  section: { fontSize: 20, fontWeight: '600', color: '#000000', marginTop: 12 },
  body: { fontSize: 17, color: '#1A1A1A' },
});

const styles = StyleSheet.create({
  button: {
    minHeight: 64,
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    justifyContent: 'center',
  },
  primary: { borderColor: '#0B3D91', backgroundColor: '#E8EEF9' },
  selected: { borderColor: '#0B3D91', backgroundColor: '#C9D7F0', borderWidth: 4 },
  danger: { borderColor: '#8A1C1C', backgroundColor: '#FBE9E9' },
  pressed: { opacity: 0.7 },
  title: { fontSize: 20, fontWeight: '600', color: '#0B3D91' },
  dangerText: { color: '#8A1C1C' },
  detail: { fontSize: 15, color: '#1A1A1A', marginTop: 4 },
});
