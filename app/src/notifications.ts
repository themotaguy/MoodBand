// Step 1 of an intervention (decisions.md #13): a local notification carrying the
// suggestion. Phone haptics are only felt in the hand, so the notification's
// sound/buzz gets the user's attention and the session plays once it's opened.
// Local only — no push entitlement (app.json), so free Apple ID signing works.
import * as Notifications from 'expo-notifications';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function ensurePermission(): Promise<boolean> {
  const current = await Notifications.getPermissionsAsync();
  if (current.granted) return true;
  const asked = await Notifications.requestPermissionsAsync({
    ios: { allowAlert: true, allowSound: true, allowBadge: false },
  });
  return asked.granted;
}

/** Schedule a suggestion; `quiet` (recovery cue) shows it without a sound. */
export async function scheduleSuggestion(intervention: string, body: string, seconds: number, quiet = false) {
  return Notifications.scheduleNotificationAsync({
    content: {
      title: 'MoodBand',
      body,
      data: { intervention },
      sound: quiet ? false : 'default',
    },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds },
  });
}

/** Calls `open` with the intervention id when the user taps a notification,
 * including the one that launched the app from closed. Returns a cleanup. */
export function onSuggestionOpened(open: (intervention: string) => void): () => void {
  const handle = (response: Notifications.NotificationResponse | null) => {
    if (!response || response.actionIdentifier !== Notifications.DEFAULT_ACTION_IDENTIFIER) return;
    const id = response.notification.request.content.data?.intervention;
    if (typeof id === 'string') {
      Notifications.clearLastNotificationResponse();
      open(id);
    }
  };
  handle(Notifications.getLastNotificationResponse());
  const sub = Notifications.addNotificationResponseReceivedListener(handle);
  return () => sub.remove();
}
