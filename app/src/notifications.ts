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

/** Where a replayed suggestion came from: the recorded day and the model's mood. */
export type ReplayContext = { participant: string; date: string; time: string; mood: string };

/** Schedule a suggestion; `quiet` (recovery cue) shows it without a sound. */
export async function scheduleSuggestion(intervention: string, body: string, seconds: number, quiet = false) {
  return Notifications.scheduleNotificationAsync({
    content: content(intervention, body, quiet),
    trigger: { type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds },
  });
}

/** Schedule a replayed suggestion for a set time, so it arrives with the phone locked. */
export async function scheduleReplaySuggestion(intervention: string, body: string, at: Date,
                                               replay: ReplayContext, quiet = false) {
  return Notifications.scheduleNotificationAsync({
    content: content(intervention, body, quiet, replay),
    trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: at },
  });
}

export const cancelSuggestion = (id: string) => Notifications.cancelScheduledNotificationAsync(id);

function content(intervention: string, body: string, quiet: boolean, replay?: ReplayContext) {
  return { title: 'MoodBand', body, data: { intervention, ...(replay ? { replay } : {}) }, sound: quiet ? false : 'default' };
}

/** Calls `open` with the intervention id (and replay context, if any) when the user
 * taps a notification, including the one that launched the app from closed. Returns a cleanup. */
export function onSuggestionOpened(open: (intervention: string, replay?: ReplayContext) => void): () => void {
  const handle = (response: Notifications.NotificationResponse | null) => {
    if (!response || response.actionIdentifier !== Notifications.DEFAULT_ACTION_IDENTIFIER) return;
    const data = response.notification.request.content.data;
    if (typeof data?.intervention === 'string') {
      Notifications.clearLastNotificationResponse();
      open(data.intervention, data.replay as ReplayContext | undefined);
    }
  };
  handle(Notifications.getLastNotificationResponse());
  const sub = Notifications.addNotificationResponseReceivedListener(handle);
  return () => sub.remove();
}
