import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from app.config import AST_CHECKPOINT, FINAL_METRICS
from app.services.audio_decode_service import prepare_audio_for_analysis
from app.services.feature_service import extract_full_clip_features, load_feature_df

AST_MODEL_NAME = "MIT/ast-finetuned-audioset-10-10-0.4593"
AST_MODEL_ID = AST_MODEL_NAME
MODEL_SR = 16000
SEGMENT_SECONDS = 10.0
EVAL_CROP_OFFSETS = [0.0, 5.0, 10.0, 15.0, 20.0]
USE_MIXED_PRECISION = True
FULL_CLIP_SECONDS = 30.0
N_MFCC = 20

_ast_bundle = None


def _load_label_names() -> List[str]:
    if FINAL_METRICS.exists():
        with FINAL_METRICS.open("r", encoding="utf-8") as f:
            metrics = json.load(f)
        labels = metrics.get("label_names")
        if labels:
            return list(labels)

    df = load_feature_df()
    return sorted(df["genre"].dropna().astype(str).unique())


def _load_audio_segment(path, start_sec, duration_sec, sr=MODEL_SR):
    import librosa

    y, _ = librosa.load(path, sr=sr, mono=True, offset=start_sec, duration=duration_sec)
    target_len = int(sr * duration_sec)
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]
    return y.astype(np.float32)


def _load_ast_bundle():
    global _ast_bundle
    if _ast_bundle is not None:
        return _ast_bundle

    import torch
    from transformers import ASTConfig, ASTFeatureExtractor, ASTForAudioClassification

    if not AST_CHECKPOINT.exists():
        raise FileNotFoundError(f"AST checkpoint not found: {AST_CHECKPOINT}")

    label_names = _load_label_names()
    label2id = {label: idx for idx, label in enumerate(label_names)}
    id2label = {idx: label for label, idx in label2id.items()}

    config = ASTConfig(
        num_labels=len(label_names),
        label2id=label2id,
        id2label=id2label,
    )
    model = ASTForAudioClassification(config)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    state_dict = torch.load(AST_CHECKPOINT, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="At least one mel filter has all zero values.*",
            category=UserWarning,
        )
        feature_extractor = ASTFeatureExtractor()
    _ast_bundle = {
        "model": model,
        "feature_extractor": feature_extractor,
        "device": device,
        "label_names": label_names,
        "id2label": id2label,
    }
    return _ast_bundle


def model_status():
    return {
        "status": "ok" if AST_CHECKPOINT.exists() else "missing_checkpoint",
        "checkpoint": str(AST_CHECKPOINT),
        "model_id": AST_MODEL_ID,
        "lazy_loaded": _ast_bundle is not None,
        "labels": _load_label_names(),
    }


def predict_clip_with_ast(audio_path: str, offsets=EVAL_CROP_OFFSETS) -> Dict[str, object]:
    import torch

    bundle = _load_ast_bundle()
    model = bundle["model"]
    feature_extractor = bundle["feature_extractor"]
    device = bundle["device"]
    id2label = bundle["id2label"]

    all_probs = []
    with torch.no_grad():
        for offset in offsets:
            y = _load_audio_segment(audio_path, offset, SEGMENT_SECONDS, sr=MODEL_SR)
            inputs = feature_extractor(y, sampling_rate=MODEL_SR, return_tensors="pt")
            input_values = inputs["input_values"].to(device)

            with torch.amp.autocast(
                device_type=device.type,
                enabled=(USE_MIXED_PRECISION and device.type == "cuda")
            ):
                logits = model(input_values=input_values).logits

            probs = torch.softmax(logits, dim=-1).detach().cpu().numpy()[0]
            all_probs.append(probs)

    mean_probs = np.mean(np.stack(all_probs, axis=0), axis=0)
    pred_id = int(mean_probs.argmax())
    top3_idx = np.argsort(mean_probs)[::-1][:3]
    top3 = [
        {"genre": id2label[int(idx)], "probability": float(mean_probs[int(idx)])}
        for idx in top3_idx
    ]

    return {
        "pred_id": pred_id,
        "pred_genre": id2label[pred_id],
        "top3": top3,
    }


def _feature_quantile(column: str, q: float) -> float:
    df = load_feature_df()
    return float(df[column].quantile(q))


def template_dj_recommendation(pred_genre: str, feats: Dict[str, float], top3) -> str:
    tempo = feats["tempo_bpm"]
    centroid = feats["centroid_mean"]
    rms = feats["rms_mean"]

    if tempo < 85:
        tempo_desc = "slow"
    elif tempo < 120:
        tempo_desc = "moderate"
    else:
        tempo_desc = "fast"

    if rms < _feature_quantile("rms_mean", 0.33):
        energy_desc = "soft"
    elif rms < _feature_quantile("rms_mean", 0.66):
        energy_desc = "balanced"
    else:
        energy_desc = "high-energy"

    if centroid < _feature_quantile("centroid_mean", 0.33):
        tone_desc = "warm"
    elif centroid < _feature_quantile("centroid_mean", 0.66):
        tone_desc = "balanced"
    else:
        tone_desc = "bright"

    return (
        f"This track leans {pred_genre} with a {tempo_desc} tempo around "
        f"{tempo:.1f} BPM, {energy_desc} dynamics, and a {tone_desc} "
        "spectral profile. It fits a listener who wants a clear, "
        "genre-shaped mood without inventing artist metadata for the clip."
    )


def analyze_audio(audio_path: str):
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    with prepare_audio_for_analysis(str(path)) as prepared_audio:
        prediction = predict_clip_with_ast(prepared_audio.path)
        features = extract_full_clip_features(prepared_audio.path)

    top3 = prediction["top3"]
    recommendation = template_dj_recommendation(
        prediction["pred_genre"],
        features,
        top3,
    )

    return {
        "status": "ok",
        "predicted_genre": prediction["pred_genre"],
        "top3": top3,
        "features": features,
        "recommendation": recommendation,
    }

