import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { StateProvider } from '@/state';

export default function RootLayout() {
  return (
    <StateProvider>
      <Stack screenOptions={{ headerLargeTitle: false, contentStyle: { backgroundColor: '#FFFFFF' } }}>
        <Stack.Screen name="index" options={{ title: 'MoodBand' }} />
        <Stack.Screen name="session/[id]" options={{ title: 'Break', presentation: 'fullScreenModal', headerShown: false }} />
        <Stack.Screen name="haptics" options={{ title: 'Haptics test' }} />
      </Stack>
      <StatusBar style="dark" />
    </StateProvider>
  );
}
