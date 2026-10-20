"""Feedback-decision module: mood prediction + accessibility profile -> one intervention or nothing.

A just-in-time adaptive intervention (JITAI) decision rule (Nahum-Shani et al., lit
review [11]): every new prediction is a decision point; the tailoring variables are
the predicted mood and context (recent activity, time of day, the user's settings);
the intervention options are the catalog in interventions.json.

Because the classifier is modest (~0.33 balanced accuracy, 4 classes), the rule is
deliberately conservative (Koh et al. [18]):
  1. confidence gate   — act only on a confident prediction
  2. exercise filter   — high-arousal moods right after activity are ignored
  3. persistence       — the same mood in most of the last few predictions
  4. rate limits       — snooze, quiet hours, daily cap, cooldown
Happy/neutral never trigger feedback while they continue; the only positive
feedback is a recovery cue when a negative state gives way to a positive one.

Accessibility rules (three profiles) are enforced on the catalog when it is loaded:
blind users always get audio *and* haptic, low-vision users audio and haptic plus
optional high-contrast visuals, every visual cue has screen-reader text, and every
intervention has a haptic channel. Design: Docs/feedback-module-plan.md.

The module is pure Python with no dependencies, so it can run on a backend or be
ported to the app; the catalog JSON is shared as-is.
"""

import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("interventions.json")

PROFILES = ("sighted", "low_vision", "blind")
NEGATIVE_MOODS = ("stressed", "sad", "angry")
POSITIVE_MOODS = ("happy", "neutral")
# Exercise raises heart rate too, so these can't be told apart from activity
# (the "perceptual mismatch" in Koh et al. [18]).
HIGH_AROUSAL_MOODS = ("stressed", "angry")


@dataclass(frozen=True)
class Prediction:
    time: datetime
    probabilities: dict          # mood -> probability, from the classifier
    recent_steps: int = 0        # steps in the classifier's input window (30 min)


@dataclass
class UserSettings:
    profile: str = "sighted"     # one of PROFILES
    audio_available: bool = True  # False when the phone is silenced
    quiet_hours: tuple = (22, 7)  # (start hour, end hour); may wrap midnight
    snoozed_until: datetime | None = None


@dataclass(frozen=True)
class Config:
    # From simulate.py: ~1.2 interventions per person-day. Stricter thresholds cut
    # burden but not error (stressed precision ~0.31-0.37 at every threshold), so
    # this is a burden choice, not an accuracy one (decisions.md #11).
    min_confidence: float = 0.45
    min_margin: float = 0.10       # top probability must beat the runner-up by this
    persistence_window: int = 3
    persistence_required: int = 2  # same mood in 2 of the last 3 predictions
    cooldown: timedelta = timedelta(minutes=30)
    daily_cap: int = 4             # one system in Koh et al. [18] capped at four per day
    exercise_steps: int = 1000     # steps in the input window treated as "just active"
    recovery_window: timedelta = timedelta(hours=2)  # how recent a negative state must be


@dataclass(frozen=True)
class Decision:
    time: datetime
    reason: str                    # "intervene", "recovery", or why nothing was done
    mood: str | None = None
    intervention: dict | None = None

    @property
    def acts(self):
        return self.intervention is not None


class CatalogError(ValueError):
    pass


def load_catalog(path=CATALOG_PATH):
    with open(path) as f:
        catalog = json.load(f)
    validate_catalog(catalog)
    return catalog


def validate_catalog(catalog):
    """Raise CatalogError listing every violation of the accessibility rules."""
    problems = []
    patterns = catalog["haptic_patterns"]
    for name, entry in catalog["interventions"].items():
        for profile in PROFILES:
            channels = entry["profiles"].get(profile)
            where = f"{name}/{profile}"
            if channels is None:
                problems.append(f"{where}: profile missing")
                continue
            if channels.get("haptic") not in patterns:
                problems.append(f"{where}: needs a haptic channel with a defined pattern")
            if profile in ("blind", "low_vision") and "audio" not in channels:
                problems.append(f"{where}: needs audio (always audio + haptic)")
            if profile == "blind" and "visual" in channels:
                problems.append(f"{where}: must not rely on a visual cue")
            visual = channels.get("visual")
            if visual is not None:
                if not visual.get("screen_reader_text"):
                    problems.append(f"{where}: visual cue needs screen_reader_text")
                if profile == "low_vision" and not (visual.get("high_contrast") and visual.get("optional")):
                    problems.append(f"{where}: low-vision visuals must be high-contrast and optional")
    for mood, name in {**catalog["moods"], "on_demand": catalog["on_demand"]}.items():
        if name not in catalog["interventions"]:
            problems.append(f"{mood}: maps to unknown intervention {name!r}")
    if problems:
        raise CatalogError("; ".join(problems))


class FeedbackDecider:
    """Holds one user's recent history; call decide() on every new prediction."""

    def __init__(self, config=Config(), catalog=None):
        self.config = config
        self.catalog = catalog or load_catalog()
        self._recent = deque(maxlen=config.persistence_window)
        self._negative_since = None   # (mood, time) of the latest persistent negative state
        self._fired = []              # times interventions were delivered (excluding on-demand)

    def decide(self, prediction, user):
        now = prediction.time
        mood, reason = self._gate(prediction)
        self._recent.append(mood)
        if mood is None:
            return Decision(now, reason)

        persistent = self._persistent_mood()
        if persistent is None:
            return Decision(now, "not_persistent", mood)

        if persistent in NEGATIVE_MOODS:
            self._negative_since = (persistent, now)
            kind, reason = persistent, "intervene"
        elif self._recovering(now):
            self._negative_since = None
            kind, reason = "recovery", "recovery"
        else:
            return Decision(now, "positive_state", persistent)

        blocked = self._rate_limited(now, user, recovery=kind == "recovery")
        if blocked:
            return Decision(now, blocked, persistent)

        self._fired.append(now)
        return Decision(now, reason, persistent, self._resolve(self.catalog["moods"][kind], user))

    def on_demand(self, now, user):
        """The user's "I need a break" button: no gates, not counted against the cap."""
        return Decision(now, "on_demand", None, self._resolve(self.catalog["on_demand"], user))

    # -- steps ------------------------------------------------------------

    def _gate(self, prediction):
        ranked = sorted(prediction.probabilities.items(), key=lambda kv: kv[1], reverse=True)
        (top, p1), p2 = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0.0)
        if p1 < self.config.min_confidence or p1 - p2 < self.config.min_margin:
            return None, "low_confidence"
        if top in HIGH_AROUSAL_MOODS and prediction.recent_steps >= self.config.exercise_steps:
            return None, "exercise"
        return top, None

    def _persistent_mood(self):
        latest = self._recent[-1]
        if sum(m == latest for m in self._recent) >= self.config.persistence_required:
            return latest
        return None

    def _recovering(self, now):
        return (self._negative_since is not None
                and now - self._negative_since[1] <= self.config.recovery_window)

    def _rate_limited(self, now, user, recovery):
        if user.snoozed_until and now < user.snoozed_until:
            return "snoozed"
        start, end = user.quiet_hours
        in_quiet = (start <= now.hour < end) if start < end else (now.hour >= start or now.hour < end)
        if in_quiet:
            return "quiet_hours"
        if sum(t.date() == now.date() for t in self._fired) >= self.config.daily_cap:
            return "daily_cap"
        # Recovery usually follows an intervention closely, so it skips the cooldown.
        if not recovery and self._fired and now - self._fired[-1] < self.config.cooldown:
            return "cooldown"
        return None

    def _resolve(self, name, user):
        entry = self.catalog["interventions"][name]
        channels = dict(entry["profiles"][user.profile])
        deferred_audio = None
        if not user.audio_available and "audio" in channels:
            audio = channels.pop("audio")
            # Non-sighted users keep their audio cue for when sound is available again.
            if user.profile != "sighted":
                deferred_audio = audio
        return {
            "id": name,
            "prompt": entry["prompt"],
            "channels": channels,
            "haptic_pattern": self.catalog["haptic_patterns"][channels["haptic"]],
            "deferred_audio": deferred_audio,
            "alternatives": entry.get("alternatives", {}),
            "confirmation": self.catalog["confirmation"],
        }
