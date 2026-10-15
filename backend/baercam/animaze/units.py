"""Animaze "Generic Action Units" für den Programmable Tracker.

Quelle: Holotech-Doku "Animaze Programmable Tracker", Annex (157 Werte, Bereich 0..1).
Format laut offiziellem Beispiel: 157 × float32 (little endian) pro UDP-Paket.
"""

from __future__ import annotations

_NEUTRAL_HALF = {
    "HeadPitch", "HeadYaw", "HeadRoll", "BodyPitch", "BodyYaw", "BodyRoll", "BodyUpDown",
    "PursedLipsLR", "JawLR", "EyeLPupPosX", "EyeLPupPosY", "EyeRPupPosX", "EyeRPupPosY",
    "TongueLR", "TongueUD", "HandR_LR", "HandR_UD", "HandR_CloseFront", "HandL_LR", "HandL_UD",
    "HandL_CloseFront", "HandR_SoloLR", "HandR_SoloUD", "HandR_SoloTwist", "HandL_SoloLR",
    "HandL_SoloUD", "HandL_SoloTwist",
}
_NEUTRAL_ONE = {"HandR_NaturalPose", "HandL_NaturalPose"}

NAMES: list[str] = """
HeadPitch HeadYaw HeadRoll BodyPitch BodyYaw BodyRoll BodyUpDown MouthSmileUnsure Unused8
MouthSmileL MouthSmileR MouthUnsureL MouthUnsureR MouthMoveUp MouthOpen JawDrop PursedLips
PursedLipsLR MouthUnveiledTeeth MouthUnveiledTeethDown MouthUpperLipMBP MouthSmileWithTeethCovered
JawLR JawF NoseWrinklerU NoseWrinklerD BrowIntLeftU BrowIntLeftD BrowIntRightU BrowIntRightD
BrowExtLeftU BrowExtLeftD BrowExtRightU BrowExtRightD BrowCenterLeftUp BrowCenterLeftDown
BrowCenterRightUp BrowCenterRightDown BrowSqueezeInLeft BrowSqueezeInRight BrowStrechOut
EyeLClosed EyeRClosed EyeLSize EyeRSize EyeLSquint EyeRSquint EyeLPupPosX EyeLPupPosY
EyeRPupPosX EyeRPupPosY EyePupilDilate TongueOut TongueLR TongueUD PuffCheekL PuffCheekR
HandR_LR HandR_UD HandR_CloseFront HandR_NaturalPose HandL_LR HandL_UD HandL_CloseFront
HandL_NaturalPose HandR_SoloLR HandR_SoloUD HandR_SoloTwist HandL_SoloLR HandL_SoloUD
HandL_SoloTwist HandR_Finger1 HandR_Finger2 HandR_Finger3 HandR_Finger4 HandR_Finger5
HandL_Finger1 HandL_Finger2 HandL_Finger3 HandL_Finger4 HandL_Finger5 Unused81 ShoulderR_Up
ShoulderL_Up Unused84 Viseme_AA Viseme_AH Viseme_AO Viseme_AW Viseme_OY Viseme_EH Viseme_IH
Viseme_EY Viseme_Y Viseme_R Viseme_L Viseme_W Viseme_M Viseme_N Viseme_CH Viseme_FV Viseme_S
Viseme_TH Lipsync_F Lipsync_L Lipsync_TH Lipsync_Y EarLeft_U EarLeft_D EarRight_U EarRight_D
MouseAndStylus_X MouseAndStylus_Y MouseAndStylus_LeftClick MouseAndStylus_RightClick
MouseAndStylus_Scroll MouseAndStylus_Inclination MouseAndStylus_Pressure Keyboard_HandR_Finger1
Keyboard_HandR_Finger2 Keyboard_HandR_Finger3 Keyboard_HandR_Finger4 Keyboard_HandR_Finger5
Keyboard_HandL_Finger1 Keyboard_HandL_Finger2 Keyboard_HandL_Finger3 Keyboard_HandL_Finger4
Keyboard_HandL_Finger5 Gamepad_Button_A Gamepad_Button_B Gamepad_Button_X Gamepad_Button_Y
Gamepad_Button_BACK Gamepad_Button_GUIDE Gamepad_Button_START Gamepad_Button_LEFTSTICK
Gamepad_Button_RIGHTSTICK Gamepad_Button_LEFTSHOULDER Gamepad_Button_RIGHTSHOULDER
Gamepad_Button_DPAD_UP Gamepad_Button_DPAD_DOWN Gamepad_Button_DPAD_LEFT Gamepad_Button_DPAD_RIGHT
Gamepad_Button_MISC1 Gamepad_Button_PADDLE1 Gamepad_Button_PADDLE2 Gamepad_Button_PADDLE3
Gamepad_Button_PADDLE4 Gamepad_Button_TOUCHPAD Emotion_eAnger Emotion_eDisgust Emotion_eFear
Emotion_eHappiness Emotion_eSadness Emotion_eSurprise Emotion_eNeutral Procedural_Breath
""".split()

COUNT = 157
assert len(NAMES) == COUNT, len(NAMES)

INDEX: dict[str, int] = {n: i for i, n in enumerate(NAMES)}
NEUTRAL: list[float] = [0.5 if n in _NEUTRAL_HALF else 1.0 if n in _NEUTRAL_ONE else 0.0 for n in NAMES]

# Gruppen für Oberfläche, LLM-Beschreibung und Überblenden
GROUPS: dict[str, list[str]] = {
    "head_body": NAMES[0:7],
    "mouth": NAMES[7:24] + ["TongueOut", "TongueLR", "TongueUD", "PuffCheekL", "PuffCheekR"],
    "nose_brows": NAMES[24:41],
    "eyes": NAMES[41:52],
    "hands": NAMES[57:81],
    "shoulders": ["ShoulderR_Up", "ShoulderL_Up"],
    "visemes": NAMES[85:107],
    "ears": NAMES[107:111],
    "emotions": NAMES[149:156],
}
