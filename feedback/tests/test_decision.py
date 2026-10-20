"""Tests for the feedback-decision module's guardrails and accessibility rules.

Run from the repo root: python -m unittest discover -s feedback/tests -t .
"""

import copy
import unittest
from datetime import datetime, timedelta

from feedback.decision import (PROFILES, CatalogError, Config, FeedbackDecider,
                               Prediction, UserSettings, load_catalog, validate_catalog)

T0 = datetime(2026, 10, 19, 10, 0)


def probs(mood, p=0.7):
    others = [m for m in ("happy", "neutral", "sad", "stressed") if m != mood]
    return {mood: p, **{m: (1 - p) / len(others) for m in others}}


def feed(decider, moods, user=None, start=T0, step=timedelta(minutes=10), steps=0):
    """Run one prediction per mood (None = unconfident) and return the decisions."""
    user = user or UserSettings()
    out = []
    for i, mood in enumerate(moods):
        p = {"happy": 0.3, "neutral": 0.3, "sad": 0.2, "stressed": 0.2} if mood is None else probs(mood)
        out.append(decider.decide(Prediction(start + i * step, p, steps), user))
    return out


class CatalogRules(unittest.TestCase):
    def test_shipped_catalog_is_valid(self):
        load_catalog()

    def test_blind_profile_without_audio_is_rejected(self):
        catalog = copy.deepcopy(load_catalog())
        del catalog["interventions"]["breathing_break"]["profiles"]["blind"]["audio"]
        with self.assertRaisesRegex(CatalogError, "breathing_break/blind: needs audio"):
            validate_catalog(catalog)

    def test_visual_without_screen_reader_text_is_rejected(self):
        catalog = copy.deepcopy(load_catalog())
        del catalog["interventions"]["iso_music"]["profiles"]["sighted"]["visual"]["screen_reader_text"]
        with self.assertRaisesRegex(CatalogError, "screen_reader_text"):
            validate_catalog(catalog)

    def test_blind_profile_with_visual_is_rejected(self):
        catalog = copy.deepcopy(load_catalog())
        catalog["interventions"]["recovery_cue"]["profiles"]["blind"]["visual"] = {"screen_reader_text": "x"}
        with self.assertRaisesRegex(CatalogError, "must not rely on a visual cue"):
            validate_catalog(catalog)


class Guardrails(unittest.TestCase):
    def setUp(self):
        self.d = FeedbackDecider()

    def test_low_confidence_never_acts(self):
        self.assertEqual([x.reason for x in feed(self.d, [None, None, None])], ["low_confidence"] * 3)

    def test_needs_persistence(self):
        first, second = feed(self.d, ["stressed", "stressed"])
        self.assertEqual(first.reason, "not_persistent")
        self.assertTrue(second.acts)
        self.assertEqual(second.intervention["id"], "breathing_break")

    def test_happy_and_neutral_never_interrupt(self):
        decisions = feed(self.d, ["happy"] * 4 + ["neutral"] * 4)
        self.assertFalse(any(x.acts for x in decisions))

    def test_exercise_suppresses_stress_and_does_not_lead_to_recovery(self):
        decisions = feed(self.d, ["stressed"] * 3, steps=2000)
        self.assertEqual({x.reason for x in decisions}, {"exercise"})
        after = feed(self.d, ["neutral"] * 2, start=T0 + timedelta(minutes=40))
        self.assertFalse(any(x.acts for x in after))

    def test_exercise_filter_leaves_sadness_alone(self):
        self.assertTrue(feed(self.d, ["sad", "sad"], steps=2000)[-1].acts)

    def test_cooldown(self):
        decisions = feed(self.d, ["stressed"] * 5)  # every 10 minutes
        self.assertEqual([x.reason for x in decisions],
                         ["not_persistent", "intervene", "cooldown", "cooldown", "intervene"])

    def test_daily_cap(self):
        d = FeedbackDecider(Config(cooldown=timedelta(0)))
        fired = sum(x.acts for x in feed(d, ["stressed"] * 10))
        self.assertEqual(fired, 4)

    def test_quiet_hours_wrap_midnight(self):
        late = feed(self.d, ["stressed"] * 2, start=datetime(2026, 10, 19, 23, 0))
        self.assertEqual(late[-1].reason, "quiet_hours")
        early = feed(FeedbackDecider(), ["stressed"] * 2, start=datetime(2026, 10, 20, 6, 0))
        self.assertEqual(early[-1].reason, "quiet_hours")

    def test_snooze(self):
        user = UserSettings(snoozed_until=T0 + timedelta(hours=1))
        self.assertEqual(feed(self.d, ["stressed"] * 2, user)[-1].reason, "snoozed")


class Recovery(unittest.TestCase):
    def test_negative_then_positive_gives_one_recovery_cue(self):
        d = FeedbackDecider()
        decisions = feed(d, ["sad", "sad", "neutral", "neutral", "neutral", "happy"])
        self.assertEqual([x.reason for x in decisions].count("recovery"), 1)
        cue = next(x for x in decisions if x.reason == "recovery")
        self.assertEqual(cue.intervention["id"], "recovery_cue")

    def test_recovery_skips_cooldown(self):
        # Intervention at 10:10, recovery 20 minutes later: inside the cooldown.
        decisions = feed(FeedbackDecider(), ["stressed", "stressed", "neutral", "neutral"])
        self.assertEqual(decisions[-1].reason, "recovery")

    def test_no_recovery_after_a_long_gap(self):
        d = FeedbackDecider()
        feed(d, ["sad", "sad"])
        later = feed(d, ["happy", "happy"], start=T0 + timedelta(hours=4))
        self.assertEqual(later[-1].reason, "positive_state")


class Accessibility(unittest.TestCase):
    def deliver(self, profile, audio_available=True, mood="stressed"):
        user = UserSettings(profile=profile, audio_available=audio_available)
        return feed(FeedbackDecider(), [mood, mood], user)[-1].intervention

    def test_every_profile_and_mood_has_haptic(self):
        for profile in PROFILES:
            for mood in ("stressed", "sad"):
                self.assertIn("haptic", self.deliver(profile, mood=mood)["channels"], (profile, mood))

    def test_blind_gets_audio_and_haptic_never_visual(self):
        channels = self.deliver("blind")["channels"]
        self.assertIn("audio", channels)
        self.assertIn("haptic", channels)
        self.assertNotIn("visual", channels)

    def test_low_vision_visual_is_optional_high_contrast(self):
        visual = self.deliver("low_vision")["channels"]["visual"]
        self.assertTrue(visual["high_contrast"] and visual["optional"])

    def test_silenced_phone_defers_audio_for_blind_user(self):
        intervention = self.deliver("blind", audio_available=False)
        self.assertEqual(set(intervention["channels"]), {"haptic"})
        self.assertIsNotNone(intervention["deferred_audio"])

    def test_silenced_phone_drops_audio_for_sighted_user(self):
        intervention = self.deliver("sighted", audio_available=False, mood="sad")
        self.assertNotIn("audio", intervention["channels"])
        self.assertIn("visual", intervention["channels"])
        self.assertIsNone(intervention["deferred_audio"])

    def test_every_intervention_is_a_suggestion_with_confirmation(self):
        intervention = self.deliver("sighted")
        self.assertTrue(intervention["prompt"].endswith("?"))
        self.assertEqual(intervention["confirmation"]["options"], ["yes", "no", "snooze"])


class OnDemand(unittest.TestCase):
    def test_on_demand_bypasses_gates_and_cap(self):
        d = FeedbackDecider()
        user = UserSettings(snoozed_until=T0 + timedelta(days=1))
        decision = d.on_demand(T0, user)
        self.assertEqual(decision.intervention["id"], "breathing_break")
        self.assertEqual(d._fired, [])


if __name__ == "__main__":
    unittest.main()
