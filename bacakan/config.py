"""Konstanta yang dipakai bersama oleh antarmuka web dan terminal."""

VOICES = tuple([f"M{i}" for i in range(1, 6)] + [f"F{i}" for i in range(1, 6)])
DEFAULT_VOICE = "F1"
LANGUAGE = "id"

DEFAULT_SPEED = 1.05
MIN_SPEED = 0.1
MAX_SPEED = 3.0

DEFAULT_TOTAL_STEPS = 8
MIN_TOTAL_STEPS = 1
MAX_TOTAL_STEPS = 100
MAX_TEXT_LENGTH = 100_000

DEFAULT_FORMAT = "wav"
AUDIO_MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg"}
