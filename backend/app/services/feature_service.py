import pandas as pd
from app.config import FEATURE_CSV

FULL_CLIP_SR = 22050
FULL_CLIP_SECONDS = 30.0
N_MFCC = 40

_feature_df = None

def load_feature_df():
    global _feature_df
    if _feature_df is None:
        if not FEATURE_CSV.exists():
            raise FileNotFoundError(f"Feature CSV not found: {FEATURE_CSV}")
        _feature_df = pd.read_csv(FEATURE_CSV)
    return _feature_df


def load_audio_full(path, sr=FULL_CLIP_SR, duration=FULL_CLIP_SECONDS):
    import librosa
    import numpy as np

    y, _ = librosa.load(path, sr=sr, mono=True, duration=duration)
    target_len = int(sr * duration)
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]
    return y


def _as_float(value):
    import numpy as np

    arr = np.asarray(value).reshape(-1)
    return float(arr[0]) if len(arr) else 0.0


def extract_full_clip_features(path):
    import librosa

    y = load_audio_full(path, sr=FULL_CLIP_SR, duration=FULL_CLIP_SECONDS)
    mfcc = librosa.feature.mfcc(y=y, sr=FULL_CLIP_SR, n_mfcc=N_MFCC)
    rms = librosa.feature.rms(y=y)
    centroid = librosa.feature.spectral_centroid(y=y, sr=FULL_CLIP_SR)
    zcr = librosa.feature.zero_crossing_rate(y)
    tempo, _ = librosa.beat.beat_track(y=y, sr=FULL_CLIP_SR)

    feats = {
        "tempo_bpm": _as_float(tempo),
        "rms_mean": float(rms.mean()),
        "rms_std": float(rms.std()),
        "centroid_mean": float(centroid.mean()),
        "centroid_std": float(centroid.std()),
        "zcr_mean": float(zcr.mean()),
        "zcr_std": float(zcr.std()),
    }

    mfcc_means = mfcc.mean(axis=1)
    mfcc_stds = mfcc.std(axis=1)
    for i in range(N_MFCC):
        feats[f"mfcc_mean_{i}"] = float(mfcc_means[i])
        feats[f"mfcc_std_{i}"] = float(mfcc_stds[i])

    return feats
