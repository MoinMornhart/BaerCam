"""Test-Clips für Etappe 1 (prüfen, ob VMC und Programmable Tracker in Animaze ankommen).

Das sind KEINE Grenzen – in Etappe 2 erzeugt die KI beliebige Clips im selben Format.
"""

from __future__ import annotations

TEST_CLIPS: dict[str, dict] = {
    "winken": {
        "name": "Winken (VMC)",
        "duration": 2.4,
        "bones": {
            "RightUpperArm": [[0, 0, 0, -70], [0.4, 0, 0, 75], [2.0, 0, 0, 75], [2.4, 0, 0, -70]],
            "RightLowerArm": [[0, 0, 10, 0], [0.4, 0, 60, 0], [0.7, 0, 20, 0], [1.0, 0, 60, 0], [1.3, 0, 20, 0], [1.6, 0, 60, 0], [2.4, 0, 10, 0]],
            "RightHand": [[0, 0, 0, 0], [0.4, 0, 0, 0], [0.7, 0, 0, 25], [1.0, 0, 0, -25], [1.3, 0, 0, 25], [1.6, 0, 0, 0]],
            "Head": [[0, 0, 0, 0], [0.5, 0, 0, 8], [2.0, 0, 0, 8], [2.4, 0, 0, 0]],
        },
        "face": {"MouthSmileL": [[0, 0], [0.4, 0.9], [2.0, 0.9], [2.4, 0]], "MouthSmileR": [[0, 0], [0.4, 0.9], [2.0, 0.9], [2.4, 0]]},
    },
    "jubeln": {
        "name": "Arme hoch (VMC)",
        "duration": 2.0,
        "bones": {
            "LeftUpperArm": [[0, 0, 0, 70], [0.5, 0, 0, -60], [1.5, 0, 0, -60], [2.0, 0, 0, 70]],
            "RightUpperArm": [[0, 0, 0, -70], [0.5, 0, 0, 60], [1.5, 0, 0, 60], [2.0, 0, 0, -70]],
            "Spine": [[0, 0, 0, 0], [0.5, -8, 0, 0], [1.5, -8, 0, 0], [2.0, 0, 0, 0]],
        },
        "face": {"JawDrop": [[0, 0], [0.5, 0.7], [1.5, 0.7], [2.0, 0]], "Emotion_eHappiness": [[0, 0], [0.5, 1], [1.5, 1], [2.0, 0]]},
    },
    "zwinkern": {
        "name": "Zwinkern + Grinsen (Tracker)",
        "duration": 1.6,
        "face": {
            "EyeRClosed": [[0, 0], [0.25, 1], [0.6, 1], [0.85, 0]],
            "MouthSmileL": [[0, 0], [0.3, 1], [1.2, 1], [1.6, 0]],
            "MouthSmileR": [[0, 0], [0.3, 0.6], [1.2, 0.6], [1.6, 0]],
            "BrowExtLeftU": [[0, 0], [0.3, 0.8], [1.2, 0.8], [1.6, 0]],
            "HeadRoll": [[0, 0.5], [0.3, 0.6], [1.2, 0.6], [1.6, 0.5]],
        },
    },
    "mittelfinger": {
        "name": "Mittelfinger (Tracker-Finger + VMC-Arm)",
        "duration": 2.6,
        "bones": {
            "RightUpperArm": [[0, 0, 0, -70], [0.5, -40, -30, 10], [2.1, -40, -30, 10], [2.6, 0, 0, -70]],
            "RightLowerArm": [[0, 0, 10, 0], [0.5, 0, 100, 0], [2.1, 0, 100, 0], [2.6, 0, 10, 0]],
            "RightIndexProximal": [[0, 0, 0, 0], [0.5, 0, 0, 90], [2.1, 0, 0, 90], [2.6, 0, 0, 0]],
            "RightIndexIntermediate": [[0, 0, 0, 0], [0.5, 0, 0, 90], [2.1, 0, 0, 90], [2.6, 0, 0, 0]],
            "RightRingProximal": [[0, 0, 0, 0], [0.5, 0, 0, 90], [2.1, 0, 0, 90], [2.6, 0, 0, 0]],
            "RightRingIntermediate": [[0, 0, 0, 0], [0.5, 0, 0, 90], [2.1, 0, 0, 90], [2.6, 0, 0, 0]],
            "RightLittleProximal": [[0, 0, 0, 0], [0.5, 0, 0, 90], [2.1, 0, 0, 90], [2.6, 0, 0, 0]],
            "RightLittleIntermediate": [[0, 0, 0, 0], [0.5, 0, 0, 90], [2.1, 0, 0, 90], [2.6, 0, 0, 0]],
            "RightThumbProximal": [[0, 0, 0, 0], [0.5, 0, 0, 50], [2.1, 0, 0, 50], [2.6, 0, 0, 0]],
        },
        "face": {
            "HandR_Finger1": [[0, 0], [0.5, 1], [2.1, 1], [2.6, 0]],
            "HandR_Finger2": [[0, 0], [0.5, 1], [2.1, 1], [2.6, 0]],
            "HandR_Finger3": [[0, 0], [0.5, 0], [2.1, 0], [2.6, 0]],
            "HandR_Finger4": [[0, 0], [0.5, 1], [2.1, 1], [2.6, 0]],
            "HandR_Finger5": [[0, 0], [0.5, 1], [2.1, 1], [2.6, 0]],
            "HandR_NaturalPose": [[0, 1], [0.5, 0], [2.1, 0], [2.6, 1]],
            "HandR_UD": [[0, 0.5], [0.5, 0.9], [2.1, 0.9], [2.6, 0.5]],
            "MouthSmileUnsure": [[0, 0], [0.5, 0.6], [2.1, 0.6], [2.6, 0]],
            "BrowIntLeftD": [[0, 0], [0.5, 0.7], [2.1, 0.7], [2.6, 0]],
            "BrowIntRightD": [[0, 0], [0.5, 0.7], [2.1, 0.7], [2.6, 0]],
        },
    },
}
