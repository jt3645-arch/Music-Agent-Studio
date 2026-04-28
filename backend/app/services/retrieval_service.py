import re
from typing import Dict, List

import numpy as np
import pandas as pd

from app.services.feature_service import load_feature_df


FEATURE_COLUMNS = ["tempo_bpm", "rms_mean", "centroid_mean"]
OUTPUT_COLUMNS = [
    "clip_id",
    "genre",
    "audio_path",
    "tempo_bpm",
    "rms_mean",
    "centroid_mean",
    "final_score",
]

LOW_ENERGY_TERMS = {
    "relax",
    "relaxing",
    "calm",
    "late night",
    "study",
    "soft",
    "chill",
    "mellow",
}
HIGH_ENERGY_TERMS = {
    "energetic",
    "party",
    "dance",
    "workout",
    "gym",
    "fast",
    "hype",
}
WARM_TERMS = {"warm", "smooth", "night", "cozy"}
BRIGHT_TERMS = {"bright", "sparkling", "crispy"}

LOW_QUANTILE = 0.25
MID_QUANTILE = 0.50
HIGH_QUANTILE = 0.75
LOW_CENTROID_QUANTILE = 0.30
HIGH_CENTROID_QUANTILE = 0.70
BRIGHT_CENTROID_QUANTILE = 0.80
WARM_CENTROID_QUANTILE = 0.25
GENRE_BONUS = 0.35
FEATURE_WEIGHTS = np.array([1.20, 1.00, 1.10], dtype=float)


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _contains_term(normalized_query: str, term: str) -> bool:
    return f" {_normalize_text(term)} " in f" {normalized_query} "


def _matched_terms(normalized_query: str, terms: set[str]) -> List[str]:
    return sorted(term for term in terms if _contains_term(normalized_query, term))


def _genre_aliases(genre: str) -> set[str]:
    normalized = _normalize_text(genre)
    aliases = {normalized, normalized.replace(" ", "")}
    if normalized == "hip hop":
        aliases.update({"hip-hop", "hip hop", "hiphop"})
    return aliases


def _detect_preferred_genres(query: str, df: pd.DataFrame) -> List[str]:
    normalized_query = _normalize_text(query)
    detected = []

    for genre in sorted(df["genre"].dropna().astype(str).unique()):
        aliases = _genre_aliases(genre)

        if "genre_key" in df.columns:
            genre_keys = df.loc[df["genre"].astype(str) == genre, "genre_key"]
            for genre_key in genre_keys.dropna().astype(str).unique():
                aliases.update(_genre_aliases(genre_key))

        if any(_contains_term(normalized_query, alias) for alias in aliases):
            detected.append(genre)

    return detected


def _feature_quantiles(df: pd.DataFrame) -> Dict[str, Dict[float, float]]:
    return {
        col: {
            LOW_QUANTILE: float(df[col].quantile(LOW_QUANTILE)),
            MID_QUANTILE: float(df[col].quantile(MID_QUANTILE)),
            HIGH_QUANTILE: float(df[col].quantile(HIGH_QUANTILE)),
            LOW_CENTROID_QUANTILE: float(df[col].quantile(LOW_CENTROID_QUANTILE)),
            HIGH_CENTROID_QUANTILE: float(df[col].quantile(HIGH_CENTROID_QUANTILE)),
            BRIGHT_CENTROID_QUANTILE: float(df[col].quantile(BRIGHT_CENTROID_QUANTILE)),
            WARM_CENTROID_QUANTILE: float(df[col].quantile(WARM_CENTROID_QUANTILE)),
        }
        for col in FEATURE_COLUMNS
    }


def parse_text_to_targets(query: str, df: pd.DataFrame) -> Dict[str, object]:
    normalized_query = _normalize_text(query)
    quantiles = _feature_quantiles(df)

    low_energy_matches = _matched_terms(normalized_query, LOW_ENERGY_TERMS)
    high_energy_matches = _matched_terms(normalized_query, HIGH_ENERGY_TERMS)
    warm_matches = _matched_terms(normalized_query, WARM_TERMS)
    bright_matches = _matched_terms(normalized_query, BRIGHT_TERMS)
    preferred_genres = _detect_preferred_genres(query, df)

    targets = {
        col: quantiles[col][MID_QUANTILE]
        for col in FEATURE_COLUMNS
    }
    explanation_parts = ["Started from median dataset audio features."]

    if low_energy_matches and not high_energy_matches:
        targets["tempo_bpm"] = quantiles["tempo_bpm"][LOW_QUANTILE]
        targets["rms_mean"] = quantiles["rms_mean"][LOW_QUANTILE]
        targets["centroid_mean"] = quantiles["centroid_mean"][LOW_CENTROID_QUANTILE]
        explanation_parts.append(
            "Relaxed/calm terms target lower tempo, lower loudness, and warmer timbre."
        )
    elif high_energy_matches and not low_energy_matches:
        targets["tempo_bpm"] = quantiles["tempo_bpm"][HIGH_QUANTILE]
        targets["rms_mean"] = quantiles["rms_mean"][HIGH_QUANTILE]
        targets["centroid_mean"] = quantiles["centroid_mean"][HIGH_CENTROID_QUANTILE]
        explanation_parts.append(
            "Energetic terms target higher tempo, higher loudness, and brighter timbre."
        )
    elif low_energy_matches and high_energy_matches:
        explanation_parts.append(
            "Mixed calm and energetic terms were found, so tempo and loudness stayed near the median."
        )

    if warm_matches and not bright_matches:
        targets["centroid_mean"] = quantiles["centroid_mean"][WARM_CENTROID_QUANTILE]
        explanation_parts.append("Warm/smooth/cozy terms lower the centroid target.")
    elif bright_matches and not warm_matches:
        targets["centroid_mean"] = quantiles["centroid_mean"][BRIGHT_CENTROID_QUANTILE]
        explanation_parts.append("Bright/sparkling/crispy terms raise the centroid target.")
    elif warm_matches and bright_matches:
        explanation_parts.append(
            "Mixed warm and bright terms were found, so centroid stayed near its current target."
        )

    if preferred_genres:
        explanation_parts.append(
            f"Detected preferred genre(s): {', '.join(preferred_genres)}."
        )

    return {
        "tempo_bpm": targets["tempo_bpm"],
        "rms_mean": targets["rms_mean"],
        "centroid_mean": targets["centroid_mean"],
        "preferred_genres": preferred_genres,
        "explanation": " ".join(explanation_parts),
    }


def retrieve_from_text(query: str, top_k: int = 5):
    df = load_feature_df().copy()

    missing_columns = [col for col in OUTPUT_COLUMNS[:-1] if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Feature CSV missing required columns: {missing_columns}")

    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=FEATURE_COLUMNS)
    parsed_targets = parse_text_to_targets(query, df)

    target_vector = np.array(
        [float(parsed_targets[col]) for col in FEATURE_COLUMNS],
        dtype=float,
    )
    means = df[FEATURE_COLUMNS].mean().to_numpy(dtype=float)
    stds = df[FEATURE_COLUMNS].std().replace(0, 1).to_numpy(dtype=float)

    feature_matrix = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    z_feature_matrix = (feature_matrix - means) / stds
    z_target_vector = (target_vector - means) / stds

    weighted_squared_distance = FEATURE_WEIGHTS * (
        z_feature_matrix - z_target_vector
    ) ** 2
    df["final_score"] = np.sqrt(weighted_squared_distance.sum(axis=1))

    preferred_genres = set(parsed_targets["preferred_genres"])
    if preferred_genres:
        genre_match = df["genre"].isin(preferred_genres)
        df.loc[genre_match, "final_score"] = (
            df.loc[genre_match, "final_score"] - GENRE_BONUS
        ).clip(lower=0)

    limit = max(int(top_k), 0)
    results_df = (
        df.sort_values("final_score", ascending=True)
        .head(limit)
        .loc[:, OUTPUT_COLUMNS]
        .copy()
    )

    for col in FEATURE_COLUMNS + ["final_score"]:
        results_df[col] = results_df[col].astype(float).round(6)

    return {
        "status": "ok",
        "parsed_targets": parsed_targets,
        "results": results_df.to_dict(orient="records"),
        "explanation": parsed_targets["explanation"],
    }
