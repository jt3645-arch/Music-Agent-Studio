"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  analyzeAudio,
  getLlmProviderStatus,
  planPlaylist,
  retrieveTracks,
  sendAgentImageMessage,
  sendAgentMessage,
  setLlmProvider,
} from "../lib/api";
import type {
  AgentPlaylistPlan,
  AgentPreferences,
  AgentResponse,
  AgentSong,
  AnalyzeResponse,
  LlmProviderName,
  LlmProviderStatus,
  PlaylistResponse,
  PlaylistStage,
  PlaylistTrack,
  RetrievalTrack,
  RetrieveResponse,
  VisualProfile,
} from "../lib/api";

type RequestState = "idle" | "loading" | "success" | "error";

type IconName =
  | "headphones"
  | "music"
  | "waveform"
  | "disc"
  | "playlist"
  | "equalizer"
  | "sparkles"
  | "play"
  | "image"
  | "external";

type AgentChatMessage = {
  id: string;
  role: "user" | "agent";
  content: string;
  result?: AgentResponse;
  imagePreview?: string;
};

const DEFAULT_RETRIEVAL_QUERY = "relaxing calm late-night jazz";
const DEFAULT_PLAYLIST_GOAL = "40-minute workout playlist";

const ANALYZE_ERROR_MESSAGE =
  "We couldn't analyze this audio file. Please try another song.";
const DISCOVERY_ERROR_MESSAGE =
  "We couldn't find matching songs for this request. Please try a different description.";
const PLAYLIST_ERROR_MESSAGE =
  "We couldn't create this playlist plan. Please adjust the request and try again.";
const AGENT_ERROR_MESSAGE =
  "I couldn't shape that music request yet. Please try a different phrasing.";

const AGENT_EXAMPLES = [
  "Make me a 40-minute workout playlist",
  "Create a 60-minute late-night study mix",
  "Find relaxing jazz for reading",
  "Make it more energetic",
  "More rock, less hip-hop",
  "Shorten the cooldown",
  "Recommend BGM for this photo",
  "Match this visual mood",
  "Find short-video background music",
  "Make it more cinematic",
  "Make it more upbeat",
];

const DISCOVERY_EXAMPLES = [
  "Relaxing jazz for reading",
  "Warm classical for late night",
  "Energetic hip-hop for the gym",
  "Bright pop for commuting",
];

const PLAYLIST_EXAMPLES = [
  "40-minute workout playlist",
  "60-minute late-night study playlist",
  "30-minute commute playlist",
  "45-minute dinner background playlist",
];

const PROVIDER_LABELS: Record<LlmProviderName, string> = {
  openai: "OpenAI",
  deepseek: "DeepSeek",
  qwen: "Qwen",
  offline: "Offline fallback",
};

const PROVIDER_OPTIONS: LlmProviderName[] = [
  "openai",
  "deepseek",
  "qwen",
  "offline",
];

function Icon({ name }: { name: IconName }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  if (name === "headphones") {
    return (
      <svg {...common}>
        <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
        <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3v5Z" />
        <path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3v5Z" />
      </svg>
    );
  }

  if (name === "music") {
    return (
      <svg {...common}>
        <path d="M9 18V5l12-2v13" />
        <circle cx="6" cy="18" r="3" />
        <circle cx="18" cy="16" r="3" />
      </svg>
    );
  }

  if (name === "waveform") {
    return (
      <svg {...common}>
        <path d="M3 12h2" />
        <path d="M7 6v12" />
        <path d="M11 9v6" />
        <path d="M15 4v16" />
        <path d="M19 8v8" />
        <path d="M22 12h-1" />
      </svg>
    );
  }

  if (name === "disc") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3v3" />
        <path d="M21 12h-3" />
      </svg>
    );
  }

  if (name === "playlist") {
    return (
      <svg {...common}>
        <path d="M4 6h12" />
        <path d="M4 12h10" />
        <path d="M4 18h7" />
        <path d="M18 15v6" />
        <path d="M21 18h-6" />
      </svg>
    );
  }

  if (name === "equalizer") {
    return (
      <svg {...common}>
        <path d="M4 21v-7" />
        <path d="M4 10V3" />
        <path d="M12 21v-9" />
        <path d="M12 8V3" />
        <path d="M20 21v-5" />
        <path d="M20 12V3" />
        <path d="M2 14h4" />
        <path d="M10 8h4" />
        <path d="M18 16h4" />
      </svg>
    );
  }

  if (name === "sparkles") {
    return (
      <svg {...common}>
        <path d="M12 3 9.8 8.8 4 11l5.8 2.2L12 19l2.2-5.8L20 11l-5.8-2.2L12 3Z" />
        <path d="M5 3v4" />
        <path d="M3 5h4" />
        <path d="M19 17v4" />
        <path d="M17 19h4" />
      </svg>
    );
  }

  if (name === "image") {
    return (
      <svg {...common}>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <circle cx="8.5" cy="10" r="1.5" />
        <path d="m21 15-5-5L5 19" />
      </svg>
    );
  }

  if (name === "external") {
    return (
      <svg {...common}>
        <path d="M15 3h6v6" />
        <path d="M10 14 21 3" />
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      </svg>
    );
  }

  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="9" />
      <path d="m10 8 6 4-6 4V8Z" fill="currentColor" stroke="none" />
    </svg>
  );
}

function formatNumber(value: unknown, digits = 3) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "Unavailable";
  }

  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function probabilityPercent(value: unknown) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }

  const normalized = value > 1 ? value : value * 100;
  return Math.max(0, Math.min(100, normalized));
}

function formatPercent(value: unknown) {
  return `${Math.round(probabilityPercent(value))}%`;
}

function songSearchQuery(song: AgentSong) {
  const title = song.title?.trim();
  const artist = song.artist?.trim();
  return [title, artist].filter(Boolean).join(" ");
}

function songTitleQuery(song: AgentSong) {
  const title = song.title?.trim() ?? "";
  const cleaned = title
    .replace(
      /\s*\((?=[^)]*(cover|remix|version|edit|live|acoustic|feat\.?|ft\.?|with|by))[^)]*\)/gi,
      "",
    )
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || title;
}

function spotifyFallbackUrl(song: AgentSong) {
  const query = songSearchQuery(song);
  return query ? `https://open.spotify.com/search/${encodeURIComponent(query)}` : "";
}

function neteaseFallbackUrl(song: AgentSong) {
  const query = songTitleQuery(song);
  return query
    ? `https://music.163.com/#/search/m/?s=${encodeURIComponent(query)}&type=1`
    : "";
}

function isNeteaseSearchUrl(value?: string | null) {
  return Boolean(value && /music\.163\.com\/.*search/i.test(value));
}

function songPlatformLinks(song: AgentSong) {
  if (!song.title?.trim() || !song.artist?.trim()) {
    return {
      spotify: "",
      netease: "",
    };
  }

  return {
    spotify: song.spotify_url || spotifyFallbackUrl(song),
    netease:
      song.netease_url && !isNeteaseSearchUrl(song.netease_url)
        ? song.netease_url
        : neteaseFallbackUrl(song),
  };
}

function displayTrackName(track: PlaylistTrack | RetrievalTrack) {
  return track.clip_id || "Untitled cue";
}

const COLOR_KEYWORDS: Array<[string, string]> = [
  ["cherry", "#ff9fbd"],
  ["blossom", "#ffc2d6"],
  ["pink", "#f7a6c7"],
  ["rose", "#ff8fa3"],
  ["red", "#c95f55"],
  ["brick", "#b85c4a"],
  ["orange", "#f29b55"],
  ["amber", "#f2bd69"],
  ["gold", "#e6bd5e"],
  ["yellow", "#f2d36b"],
  ["spring", "#a7e978"],
  ["botanical", "#7bd88f"],
  ["nature", "#78c87d"],
  ["green", "#74c77a"],
  ["mint", "#8ce8c8"],
  ["teal", "#63e0d5"],
  ["cyan", "#74d4f5"],
  ["sky", "#8dc8ff"],
  ["blue", "#7bb7ff"],
  ["navy", "#253a66"],
  ["violet", "#bda3ff"],
  ["purple", "#9f8cff"],
  ["pastel", "#d8c9ff"],
  ["cream", "#f3e5c6"],
  ["ivory", "#f5f0dc"],
  ["white", "#f5f3ea"],
  ["stone", "#a9aaa1"],
  ["gray", "#9da4a5"],
  ["grey", "#9da4a5"],
  ["black", "#202426"],
  ["night", "#222a34"],
  ["brown", "#9a6a4f"],
  ["wood", "#b4845f"],
  ["warm", "#f0b36a"],
  ["bright", "#a6e8ff"],
  ["cinematic", "#8f99ad"],
  ["urban", "#8c9697"],
  ["architectural", "#b9b6aa"],
];

const PALETTE_FALLBACK_COLORS = [
  "#63e0d5",
  "#a7e978",
  "#f2bd69",
  "#ff9fbd",
  "#bda3ff",
  "#8dc8ff",
];

function isCssColorValue(value: string) {
  return (
    /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(value) ||
    /^rgba?\(/i.test(value) ||
    /^hsla?\(/i.test(value)
  );
}

function resolvePaletteColor(value: unknown, index: number) {
  if (typeof value !== "string") {
    return PALETTE_FALLBACK_COLORS[index % PALETTE_FALLBACK_COLORS.length];
  }

  const text = value.trim();
  if (isCssColorValue(text)) {
    return text;
  }

  const normalized = text.toLowerCase();
  const match = COLOR_KEYWORDS.find(([keyword]) => normalized.includes(keyword));
  return match?.[1] ?? PALETTE_FALLBACK_COLORS[index % PALETTE_FALLBACK_COLORS.length];
}

function hexToRgb(value: string) {
  const hex = value.replace("#", "").trim();
  if (![3, 6, 8].includes(hex.length)) {
    return null;
  }

  const expanded =
    hex.length === 3
      ? hex
          .split("")
          .map((part) => `${part}${part}`)
          .join("")
      : hex;
  const parsed = Number.parseInt(expanded, 16);
  if (Number.isNaN(parsed)) {
    return null;
  }

  return {
    r: (parsed >> 16) & 255,
    g: (parsed >> 8) & 255,
    b: parsed & 255,
  };
}

function paletteTextColor(background: string) {
  const rgb = hexToRgb(background);
  if (!rgb) {
    return "#07100f";
  }

  const luminance = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
  return luminance > 0.58 ? "#07100f" : "#f7f8f4";
}

function paletteBackground(background: string) {
  if (/^#([0-9a-f]{6})$/i.test(background)) {
    return `linear-gradient(135deg, ${background}, ${background}cc)`;
  }

  return background;
}

function paletteLabel(value: unknown) {
  if (typeof value !== "string") {
    return "Color";
  }

  const text = value.trim();
  return isCssColorValue(text) ? "" : text;
}

function getNumber(value: unknown) {
  return typeof value === "number" && !Number.isNaN(value) ? value : undefined;
}

function describeEnergy(value: unknown) {
  const energy = getNumber(value);

  if (energy === undefined) {
    return "Balanced";
  }

  if (energy >= 0.12) {
    return "High energy";
  }

  if (energy >= 0.06) {
    return "Medium energy";
  }

  return "Low energy";
}

function describeTone(value: unknown) {
  const brightness = getNumber(value);

  if (brightness === undefined) {
    return "Balanced tone";
  }

  if (brightness >= 2800) {
    return "Bright tone";
  }

  if (brightness >= 1600) {
    return "Warm tone";
  }

  return "Soft tone";
}

function describeTexture(value: unknown) {
  const texture = getNumber(value);

  if (texture === undefined) {
    return "Smooth";
  }

  if (texture >= 0.12) {
    return "Crisp";
  }

  if (texture >= 0.06) {
    return "Detailed";
  }

  return "Smooth";
}

function energyPercentForStage(
  stage: PlaylistStage,
  index: number,
  totalStages: number,
) {
  const energy = `${stage.stage} ${stage.energy_hint ?? ""}`.toLowerCase();

  if (energy.includes("peak") || energy.includes("high")) {
    return 88;
  }

  if (energy.includes("workout") || energy.includes("energetic")) {
    return 82;
  }

  if (energy.includes("build") || energy.includes("medium")) {
    return 66;
  }

  if (
    energy.includes("warm") ||
    energy.includes("calm") ||
    energy.includes("low")
  ) {
    return 38;
  }

  if (energy.includes("cool") || energy.includes("down")) {
    return 30;
  }

  const midpoint = Math.max(1, totalStages - 1);
  return 45 + Math.round((index / midpoint) * 28);
}

function timeRanges(stages: PlaylistStage[]) {
  let cursor = 0;

  return stages.map((stage) => {
    const start = cursor;
    const minutes = Number(stage.minutes) || 0;
    cursor += minutes;

    return {
      start,
      end: cursor,
    };
  });
}

function SectionHeading({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="section-heading">
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-state" role="alert">
      <div className="error-mark" aria-hidden="true">
        !
      </div>
      <div>
        <strong>Please try again</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function LoadingState({
  title,
  text,
  rows = 3,
}: {
  title: string;
  text: string;
  rows?: number;
}) {
  return (
    <div
      className="loading-state"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="loading-copy">
        <span className="loading-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <div>
          <strong>{title}</strong>
          <p>{text}</p>
        </div>
      </div>

      <div className="skeleton-stack" aria-hidden="true">
        {Array.from({ length: rows }).map((_, index) => (
          <div className="skeleton-row" key={index}>
            <span />
            <span />
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption?: string;
}) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {caption ? <p>{caption}</p> : null}
    </div>
  );
}

function ExampleButtons({
  examples,
  onSelect,
}: {
  examples: string[];
  onSelect: (value: string) => void;
}) {
  return (
    <div className="example-row">
      {examples.map((example) => (
        <button
          className="example-chip"
          key={example}
          type="button"
          onClick={() => onSelect(example)}
        >
          {example}
        </button>
      ))}
    </div>
  );
}

function SongRecommendationCards({ songs }: { songs: AgentSong[] }) {
  if (!songs.length) {
    return null;
  }

  return (
    <div className="agent-song-grid">
      {songs.map((song, index) => {
        const links = songPlatformLinks(song);

        return (
          <article
            className="agent-song-card"
            key={`${song.title}-${song.artist}-${index}`}
          >
            <div className="song-card-art" aria-hidden="true">
              <Icon name="music" />
            </div>
            <div className="song-card-copy">
              <div className="track-topline">
                <span>{song.stage ? song.stage : "Recommended Song"}</span>
                <span className="score-badge">
                  {song.genre ?? song.mood ?? "Similar Mood"}
                </span>
              </div>
              <h3>
                {links.spotify ? (
                  <a
                    href={links.spotify}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open ${song.title} by ${song.artist} on Spotify`}
                  >
                    {song.title}
                    <Icon name="external" />
                  </a>
                ) : (
                  song.title
                )}
              </h3>
              <strong>{song.artist}</strong>
              {song.use_case ? (
                <span className="use-case-chip">{song.use_case}</span>
              ) : null}
              <p>{song.reason}</p>
              {(links.spotify || links.netease) ? (
                <div className="platform-link-row">
                  {links.spotify ? (
                    <a
                      href={links.spotify}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Icon name="play" />
                      Open on Spotify
                    </a>
                  ) : null}
                  {links.netease ? (
                    <a
                      href={links.netease}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Icon name="external" />
                      Search on NetEase
                    </a>
                  ) : null}
                </div>
              ) : null}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function SongRecommendationSection({
  eyebrow,
  title,
  songs,
}: {
  eyebrow: string;
  title: string;
  songs: AgentSong[];
}) {
  if (!songs.length) {
    return null;
  }

  return (
    <section className="song-recommendation-section">
      <div className="stage-group-title">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h3>{title}</h3>
        </div>
        <span className="soft-chip">{songs.length} songs</span>
      </div>
      <SongRecommendationCards songs={songs} />
    </section>
  );
}

function EvidencePanel({
  title,
  text,
  children,
}: {
  title: string;
  text: string;
  children: ReactNode;
}) {
  return (
    <details className="evidence-panel">
      <summary>
        <div>
          <span className="eyebrow">Sound Evidence</span>
          <strong>{title}</strong>
          <p>{text}</p>
        </div>
        <span className="soft-chip">Open</span>
      </summary>
      <div className="evidence-body">{children}</div>
    </details>
  );
}

function VisualMoodCard({ profile }: { profile: VisualProfile }) {
  const palette = profile.color_palette ?? [];
  const tags = profile.aesthetic_tags ?? [];

  return (
    <section className="visual-mood-card">
      <div className="visual-mood-head">
        <div>
          <span className="eyebrow">Visual Mood</span>
          <h3>Scene Atmosphere</h3>
        </div>
        <span className="soft-chip">{profile.energy_level ?? "Balanced"}</span>
      </div>
      {profile.scene_summary ? <p>{profile.scene_summary}</p> : null}
      {profile.visual_mood ? (
        <strong>{profile.visual_mood}</strong>
      ) : null}
      {palette.length ? (
        <div className="palette-row" aria-label="Color palette">
          {palette.map((color, index) => {
            const swatchColor = resolvePaletteColor(color, index);
            const label = paletteLabel(color);
            return (
              <span
                key={`${String(color)}-${index}`}
                title={String(color)}
                style={{
                  background: paletteBackground(swatchColor),
                  color: paletteTextColor(swatchColor),
                }}
              >
                {label}
              </span>
            );
          })}
        </div>
      ) : null}
      {tags.length ? (
        <div className="chip-list">
          {tags.map((tag) => (
            <span className="soft-chip" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      ) : null}
      {profile.recommended_music_direction ? (
        <p>{profile.recommended_music_direction}</p>
      ) : null}
      {profile.short_video_bgm_direction ? (
        <div className="recommendation-card visual-bgm-card">
          <span className="eyebrow">BGM Suggestions</span>
          <p>{profile.short_video_bgm_direction}</p>
        </div>
      ) : null}
    </section>
  );
}

function AgentPlaylistJourney({ plan }: { plan: AgentPlaylistPlan }) {
  const stages = plan.stages ?? [];

  if (!stages.length) {
    return null;
  }

  return (
    <div className="agent-playlist-journey">
      <div className="timeline-header">
        <div>
          <span className="eyebrow">Playlist Journey</span>
          <h3>Listening Arc</h3>
        </div>
      </div>

      <div className="agent-stage-rail" aria-label="Playlist journey timeline">
        {stages.map((stage, index) => (
          <div
            className="agent-stage-segment"
            key={`${stage.stage}-${index}`}
            style={{ flexGrow: Math.max(1, Number(stage.minutes) || 1) }}
          >
            <span>{stage.stage}</span>
            {stage.time_range ? (
              <small>
                {stage.time_range.start}-{stage.time_range.end} min
              </small>
            ) : null}
          </div>
        ))}
      </div>

      <div className="agent-energy-flow">
        {stages.map((stage, index) => {
          const energy = `${stage.energy_level ?? ""}`.toLowerCase();
          const height =
            energy.includes("high") || energy.includes("energetic")
              ? 88
              : energy.includes("low")
                ? 34
                : 58 + index * 5;

          return (
            <div className="agent-energy-column" key={`${stage.stage}-energy`}>
              <span style={{ height: `${Math.min(height, 94)}%` }} />
              <small>{index + 1}</small>
            </div>
          );
        })}
      </div>

      <div className="agent-stage-grid">
        {stages.map((stage, index) => (
          <article className="agent-stage-card" key={`${stage.stage}-${index}`}>
            <div className="stage-card-head">
              <span className="time-pill">
                {stage.time_range
                  ? `${stage.time_range.start}-${stage.time_range.end} min`
                  : `${formatNumber(stage.minutes, 0)} min`}
              </span>
              <span className="soft-chip">{stage.energy_level ?? "Balanced"}</span>
            </div>
            <h3>{stage.stage}</h3>
            <p>{stage.intended_mood ?? "A focused listening moment."}</p>
            <SongRecommendationCards songs={stage.recommended_songs ?? []} />
          </article>
        ))}
      </div>

      {plan.explanation ? <p className="explanation">{plan.explanation}</p> : null}
    </div>
  );
}

function AgentResult({ result }: { result: AgentResponse }) {
  return (
    <div className="agent-result-stack">
      {result.visual_profile ? (
        <VisualMoodCard profile={result.visual_profile} />
      ) : null}
      {result.playlist_plan ? (
        <AgentPlaylistJourney plan={result.playlist_plan} />
      ) : null}
      {!result.playlist_plan ? (
        <SongRecommendationCards songs={result.recommended_songs ?? []} />
      ) : null}
    </div>
  );
}

function ListeningIntentPanel({
  preferences,
  suggestions,
}: {
  preferences: AgentPreferences;
  suggestions: string[];
}) {
  const stagePlan = preferences.stage_plan ?? [];
  const visualProfile = preferences.last_visual_profile ?? preferences.visual_profile;

  return (
    <aside className="intent-panel glass-card">
      <div className="intent-panel-head">
        <Icon name="headphones" />
        <div>
          <span className="eyebrow">Listening Intent</span>
          <h3>Current Plan</h3>
        </div>
      </div>

      <div className="intent-list">
        <div>
          <span>Current Goal</span>
          <strong>{preferences.current_goal || "Ready for a music request"}</strong>
        </div>
        <div>
          <span>Duration</span>
          <strong>
            {typeof preferences.duration === "number"
              ? `${preferences.duration} min`
              : "Flexible"}
          </strong>
        </div>
        <div>
          <span>Preferred Styles</span>
          <strong>
            {(preferences.preferred_styles ?? []).length
              ? preferences.preferred_styles?.join(", ")
              : "Open"}
          </strong>
        </div>
        <div>
          <span>Disliked Styles</span>
          <strong>
            {(preferences.disliked_styles ?? []).length
              ? preferences.disliked_styles?.join(", ")
              : "None yet"}
          </strong>
        </div>
        <div>
          <span>Energy Direction</span>
          <strong>{preferences.energy_direction || "Balanced"}</strong>
        </div>
      </div>

      {stagePlan.length ? (
        <div className="intent-stage-list">
          <span className="eyebrow">Stage Plan</span>
          {stagePlan.map((stage, index) => (
            <div key={`${stage.stage}-${index}`}>
              <strong>{stage.stage}</strong>
              <span>{stage.minutes} min</span>
            </div>
          ))}
        </div>
      ) : null}

      {visualProfile ? (
        <div className="intent-stage-list">
          <span className="eyebrow">Visual Mood</span>
          <div>
            <strong>{visualProfile.visual_mood ?? "Scene Atmosphere"}</strong>
            <span>{visualProfile.energy_level ?? "Balanced"}</span>
          </div>
        </div>
      ) : null}

      <div className="intent-suggestions">
        <span className="eyebrow">Refine the Mix</span>
        {suggestions.slice(0, 4).map((suggestion) => (
          <span className="soft-chip" key={suggestion}>
            {suggestion}
          </span>
        ))}
      </div>
    </aside>
  );
}

function AdvancedProviderPanel({
  status,
  loading,
  onChange,
}: {
  status: LlmProviderStatus | null;
  loading: boolean;
  onChange: (provider: LlmProviderName) => void;
}) {
  const capabilities = status?.capabilities;

  return (
    <details className="advanced-panel">
      <summary>
        <span>Advanced</span>
        <strong>{status ? PROVIDER_LABELS[status.provider] : "Recommendation Mode"}</strong>
      </summary>
      <label>
        Recommendation Mode
        <select
          className="input"
          value={status?.provider ?? "openai"}
          disabled={loading}
          onChange={(event) => onChange(event.target.value as LlmProviderName)}
        >
          {PROVIDER_OPTIONS.map((provider) => (
            <option key={provider} value={provider}>
              {PROVIDER_LABELS[provider]}
            </option>
          ))}
        </select>
      </label>
      <div className="capability-list">
        <span className={capabilities?.supports_text ? "is-on" : ""}>
          Text recommendations
        </span>
        <span className={capabilities?.supports_vision ? "is-on" : ""}>
          Image understanding
        </span>
        <span className={capabilities?.supports_web_search ? "is-on" : ""}>
          Live web search
        </span>
      </div>
      {status && !status.configured && status.provider !== "offline" ? (
        <p>
          This mode needs a key in the environment file. Offline fallback is
          still available.
        </p>
      ) : null}
    </details>
  );
}

function ProbabilityBars({ analysis }: { analysis: AnalyzeResponse }) {
  const predictions = analysis.top3 ?? [];

  if (!predictions.length) {
    return (
      <EmptyState
        title="No confidence scores yet"
        text="Try a different song to reveal the leading genre matches."
      />
    );
  }

  return (
    <div className="probability-list" aria-label="Top genre probabilities">
      {predictions.map((item, index) => {
        const percent = probabilityPercent(item.probability);

        return (
          <div className="probability-card" key={item.genre}>
            <div className="progress-row-head">
              <span className="progress-rank">
                {String(index + 1).padStart(2, "0")}
              </span>
              <strong>{item.genre}</strong>
              <span>{formatPercent(item.probability)}</span>
            </div>
            <div
              className="progress-track"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(percent)}
              aria-label={`${item.genre} confidence ${formatPercent(
                item.probability,
              )}`}
            >
              <div
                className="progress-fill"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TargetChips({ retrieval }: { retrieval: RetrieveResponse }) {
  const targets = retrieval.parsed_targets;
  const genres = targets?.preferred_genres ?? [];

  const chips = [
    ["Mood", "Interpreted from your description"],
    ["Preferred Styles", genres.length ? genres.join(", ") : "Any style"],
    ["Energy", describeEnergy(targets?.rms_mean)],
    [
      "Tempo",
      typeof targets?.tempo_bpm === "number"
        ? `${formatNumber(targets.tempo_bpm, 0)} BPM`
        : "Flexible tempo",
    ],
    ["Tone", describeTone(targets?.centroid_mean)],
  ];

  return (
    <div className="target-chip-grid">
      {chips.map(([label, value]) => (
        <div className="target-chip" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function isPlaylistTrack(
  track: PlaylistTrack | RetrievalTrack,
): track is PlaylistTrack {
  return "stage" in track || "minutes_allocated" in track;
}

function TrackCard({
  track,
  index,
}: {
  track: PlaylistTrack | RetrievalTrack;
  index?: number;
}) {
  const minutes = isPlaylistTrack(track) ? track.minutes_allocated : undefined;

  return (
    <article className="track-card">
      <div className="track-art" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </div>

      <div className="track-main">
        <div className="track-topline">
          <span>{typeof index === "number" ? `Cue ${index + 1}` : "Match"}</span>
          <span className="score-badge">
            Match {formatNumber(track.final_score, 3)}
          </span>
        </div>
        <h3>{displayTrackName(track)}</h3>
        <div className="chip-list">
          <span className="genre-chip">{track.genre}</span>
          {typeof minutes === "number" && minutes > 0 ? (
            <span className="soft-chip">{formatNumber(minutes, 1)} min</span>
          ) : null}
        </div>
      </div>

      <div className="track-stats">
        <div>
          <span>Tempo</span>
          <strong>{formatNumber(track.tempo_bpm, 0)} BPM</strong>
        </div>
        <div>
          <span>Energy</span>
          <strong>{formatNumber(track.rms_mean, 3)}</strong>
        </div>
        <div>
          <span>Brightness</span>
          <strong>{formatNumber(track.centroid_mean, 0)}</strong>
        </div>
      </div>
    </article>
  );
}

function EnergyCurve({ stages }: { stages: PlaylistStage[] }) {
  if (!stages.length) {
    return null;
  }

  return (
    <div className="energy-curve">
      <div className="curve-header">
        <span className="eyebrow">Energy curve</span>
        <strong>Flow across the session</strong>
      </div>
      <div className="curve-bars" aria-label="Playlist energy curve">
        {stages.map((stage, index) => (
          <div className="curve-column" key={`${stage.stage}-${index}`}>
            <span
              style={{
                height: `${energyPercentForStage(stage, index, stages.length)}%`,
              }}
            />
            <small>{index + 1}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function StageCard({
  stage,
  index,
  range,
  tracks,
}: {
  stage: PlaylistStage;
  index: number;
  range: { start: number; end: number };
  tracks: PlaylistTrack[];
}) {
  return (
    <article className="stage-card">
      <div className="stage-card-head">
        <span className="time-pill">
          {formatNumber(range.start, 0)}-{formatNumber(range.end, 0)} min
        </span>
        <span className="soft-chip">Stage {index + 1}</span>
      </div>
      <h3>{stage.stage}</h3>
      <div className="stage-details">
        <div>
          <span>Intended Mood</span>
          <strong>{stage.tempo_hint ?? "Natural movement"}</strong>
        </div>
        <div>
          <span>Energy Level</span>
          <strong>{stage.energy_hint ?? "Balanced energy"}</strong>
        </div>
      </div>
      <div className="stage-track-list">
        <span>Recommended Songs</span>
        {tracks.length ? (
          tracks.slice(0, 4).map((track) => (
            <div key={`${stage.stage}-${track.clip_id}`}>
              <strong>{displayTrackName(track)}</strong>
              <em>{track.genre}</em>
            </div>
          ))
        ) : (
          <p>Curated selections will appear here.</p>
        )}
      </div>
    </article>
  );
}

function PlaylistTimeline({
  playlist,
  playlistByStage,
}: {
  playlist: PlaylistResponse;
  playlistByStage: Map<string, PlaylistTrack[]>;
}) {
  const stages = playlist.stage_plan ?? [];
  const ranges = timeRanges(stages);

  if (!stages.length) {
    return null;
  }

  return (
    <div className="timeline-system">
      <div className="timeline-header">
        <div>
          <span className="eyebrow">Stage timeline</span>
          <h3>How the playlist is structured</h3>
        </div>
      </div>

      <div className="timeline-rail" aria-label="Playlist stage timeline">
        {stages.map((stage, index) => (
          <div
            className="timeline-segment"
            key={`${stage.stage}-${index}`}
            style={{
              flexGrow: Math.max(1, Number(stage.minutes) || 1),
            }}
            title={`${stage.stage}: ${formatNumber(stage.minutes, 0)} minutes`}
          >
            <span>{stage.stage}</span>
            <small>
              {formatNumber(ranges[index].start, 0)}-
              {formatNumber(ranges[index].end, 0)} min
            </small>
          </div>
        ))}
      </div>

      <EnergyCurve stages={stages} />

      <div className="timeline-card-grid">
        {stages.map((stage, index) => (
          <StageCard
            key={`${stage.stage}-${index}`}
            stage={stage}
            index={index}
            range={ranges[index]}
            tracks={playlistByStage.get(stage.stage) ?? []}
          />
        ))}
      </div>
    </div>
  );
}

export default function HomePage() {
  const [agentInput, setAgentInput] = useState("");
  const [agentState, setAgentState] = useState<RequestState>("idle");
  const [agentError, setAgentError] = useState("");
  const [agentPreferences, setAgentPreferences] = useState<AgentPreferences>({
    preferred_styles: [],
    disliked_styles: [],
    energy_direction: "Balanced",
    last_action: "",
  });
  const [agentSuggestions, setAgentSuggestions] = useState(AGENT_EXAMPLES);
  const [agentMessages, setAgentMessages] = useState<AgentChatMessage[]>([
    {
      id: "welcome",
      role: "agent",
      content:
        "Tell me what you want to hear. I can plan a playlist journey, find real songs for a mood, or refine the mix turn by turn.",
    },
  ]);
  const [agentImage, setAgentImage] = useState<File | null>(null);
  const [agentImagePreview, setAgentImagePreview] = useState("");
  const [providerStatus, setProviderStatus] =
    useState<LlmProviderStatus | null>(null);
  const [providerState, setProviderState] = useState<RequestState>("idle");

  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analysisState, setAnalysisState] = useState<RequestState>("idle");
  const [analysisError, setAnalysisError] = useState("");

  const [retrievalQuery, setRetrievalQuery] = useState(DEFAULT_RETRIEVAL_QUERY);
  const [retrieval, setRetrieval] = useState<RetrieveResponse | null>(null);
  const [retrievalState, setRetrievalState] = useState<RequestState>("idle");
  const [retrievalError, setRetrievalError] = useState("");

  const [playlistGoal, setPlaylistGoal] = useState(DEFAULT_PLAYLIST_GOAL);
  const [playlistMinutes, setPlaylistMinutes] = useState(40);
  const [playlistGenres, setPlaylistGenres] = useState("");
  const [playlist, setPlaylist] = useState<PlaylistResponse | null>(null);
  const [playlistState, setPlaylistState] = useState<RequestState>("idle");
  const [playlistError, setPlaylistError] = useState("");

  const playlistByStage = useMemo(() => {
    const grouped = new Map<string, PlaylistTrack[]>();

    for (const track of playlist?.playlist ?? []) {
      const stage = track.stage || "Main";
      grouped.set(stage, [...(grouped.get(stage) ?? []), track]);
    }

    return grouped;
  }, [playlist]);

  const totalEstimatedMinutes = useMemo(() => {
    if (typeof playlist?.total_estimated_minutes === "number") {
      return playlist.total_estimated_minutes;
    }

    return (playlist?.stage_plan ?? []).reduce(
      (sum, stage) => sum + Number(stage.minutes || 0),
      0,
    );
  }, [playlist]);

  const analyzedSongs =
    analysis?.similar_songs ?? analysis?.recommended_songs ?? [];
  const discoverySongs = retrieval?.recommended_songs ?? [];
  const visiblePlaylistPlan = useMemo<AgentPlaylistPlan | null>(() => {
    if (!playlist) {
      return null;
    }

    if (playlist.playlist_plan) {
      return playlist.playlist_plan;
    }

    const stages = playlist.stage_plan ?? [];
    const ranges = timeRanges(stages);

    return {
      stages: stages.map((stage, index) => ({
        stage: stage.stage,
        minutes: stage.minutes,
        time_range: ranges[index],
        intended_mood: stage.tempo_hint ?? "Natural movement",
        energy_level: stage.energy_hint ?? "Balanced energy",
        recommended_songs: [],
      })),
      recommended_songs: playlist.recommended_songs ?? [],
      explanation:
        "The listening arc is organized by time, mood, and energy for the session.",
    };
  }, [playlist]);
  const playlistSongCount =
    visiblePlaylistPlan?.recommended_songs?.length ??
    playlist?.recommended_songs?.length ??
    0;

  useEffect(() => {
    let cancelled = false;
    setProviderState("loading");
    getLlmProviderStatus()
      .then((status) => {
        if (!cancelled) {
          setProviderStatus(status);
          setProviderState("success");
        }
      })
      .catch((error) => {
        console.error("Advanced settings failed", error);
        if (!cancelled) {
          setProviderState("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleProviderChange(provider: LlmProviderName) {
    setProviderState("loading");
    try {
      const status = await setLlmProvider(provider);
      setProviderStatus(status);
      setProviderState("success");
    } catch (error) {
      console.error("Advanced settings update failed", error);
      setProviderState("error");
    }
  }

  function handleAgentImageSelect(file: File | null) {
    if (agentImagePreview) {
      URL.revokeObjectURL(agentImagePreview);
    }

    if (!file) {
      setAgentImage(null);
      setAgentImagePreview("");
      return;
    }

    setAgentImage(file);
    setAgentImagePreview(URL.createObjectURL(file));
  }

  async function submitAgentTurn(message: string) {
    const image = agentImage;
    const imagePreview = agentImagePreview;
    const trimmed = message.trim() || (image ? "Recommend BGM for this photo" : "");

    if ((!trimmed && !image) || agentState === "loading") {
      return;
    }

    const userMessage: AgentChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
      imagePreview: imagePreview || undefined,
    };

    setAgentMessages((messages) => [...messages, userMessage]);
    setAgentInput("");
    setAgentImage(null);
    setAgentImagePreview("");
    setAgentError("");
    setAgentState("loading");

    try {
      const result = image
        ? await sendAgentImageMessage(trimmed, image, agentPreferences)
        : await sendAgentMessage(trimmed, agentPreferences);
      const agentMessage: AgentChatMessage = {
        id: `agent-${Date.now()}`,
        role: "agent",
        content: result.answer_text,
        result,
      };
      setAgentPreferences(result.updated_preferences ?? agentPreferences);
      setAgentSuggestions(result.follow_up_suggestions ?? AGENT_EXAMPLES);
      setAgentMessages((messages) => [...messages, agentMessage]);
      setAgentState("success");
    } catch (error) {
      console.error("Agent Studio failed", error);
      setAgentError(AGENT_ERROR_MESSAGE);
      setAgentMessages((messages) => [
        ...messages,
        {
          id: `agent-error-${Date.now()}`,
          role: "agent",
          content: AGENT_ERROR_MESSAGE,
        },
      ]);
      setAgentState("error");
    }
  }

  async function handleAgentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitAgentTurn(agentInput);
  }

  function handleAgentExample(example: string) {
    const needsVisualReference =
      example.includes("photo") ||
      example.includes("visual mood") ||
      example.includes("short-video");
    const hasVisualContext =
      agentImage ||
      agentPreferences.last_visual_profile ||
      agentPreferences.visual_profile;

    if (needsVisualReference && !hasVisualContext) {
      setAgentInput(example);
      return;
    }

    void submitAgentTurn(example);
  }

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!audioFile) {
      setAnalysisError("Choose an audio file first.");
      setAnalysisState("error");
      return;
    }

    setAnalysisState("loading");
    setAnalysisError("");

    try {
      const result = await analyzeAudio(audioFile);
      setAnalysis(result);
      setAnalysisState("success");
    } catch (error) {
      console.error("Analyze Audio failed", error);
      setAnalysisError(ANALYZE_ERROR_MESSAGE);
      setAnalysisState("error");
    }
  }

  async function handleRetrieve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRetrievalState("loading");
    setRetrievalError("");

    try {
      const result = await retrieveTracks(retrievalQuery, 6);
      setRetrieval(result);
      setRetrievalState("success");
    } catch (error) {
      console.error("Discover Music failed", error);
      setRetrievalError(DISCOVERY_ERROR_MESSAGE);
      setRetrievalState("error");
    }
  }

  async function handlePlaylist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPlaylistState("loading");
    setPlaylistError("");

    const preferredGenres = playlistGenres
      .split(",")
      .map((genre) => genre.trim())
      .filter(Boolean);

    try {
      const result = await planPlaylist({
        goal: playlistGoal,
        total_minutes: playlistMinutes,
        top_k_per_stage: 4,
        preferred_genres: preferredGenres.length ? preferredGenres : null,
      });
      setPlaylist(result);
      setPlaylistState("success");
    } catch (error) {
      console.error("Playlist Planner failed", error);
      setPlaylistError(PLAYLIST_ERROR_MESSAGE);
      setPlaylistState("error");
    }
  }

  return (
    <main className="studio-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <strong>AI Music Agent</strong>
            <span>Studio</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Studio navigation">
          <a href="#agent-studio">
            <Icon name="sparkles" />
            Agent Studio
          </a>
          <a href="#analyze-audio">Analyze Audio</a>
          <a href="#discover-music">Discover Music</a>
          <a href="#playlist-planner">Playlist Planner</a>
        </nav>

        <AdvancedProviderPanel
          status={providerStatus}
          loading={providerState === "loading"}
          onChange={handleProviderChange}
        />
      </aside>

      <div className="studio-main">
        <header className="top-header">
          <div>
            <span className="eyebrow">AI Music Agent</span>
            <h1>Music Agent Studio</h1>
            <p>
              A creative workspace for understanding songs, discovering sound,
              and shaping playlists with a guided music assistant.
            </p>
          </div>
          <div className="header-card">
            <span>Today&apos;s focus</span>
            <strong>Audio Analysis</strong>
            <p>Turn listening intent into clear music decisions.</p>
          </div>
        </header>

        <section className="studio-section agent-studio-section" id="agent-studio">
          <SectionHeading
            eyebrow="Agent Studio"
            title="Talk through the music you want"
            text="Plan a listening journey, discover real songs, and refine the mix one turn at a time."
          />

          <div className="agent-layout">
            <div className="agent-chat-panel glass-card">
              <div className="agent-chat-scroll">
                {agentMessages.map((message) => (
                  <article
                    className={`chat-message chat-message-${message.role}`}
                    key={message.id}
                  >
                    <div className="chat-avatar" aria-hidden="true">
                      <Icon
                        name={message.role === "agent" ? "headphones" : "play"}
                      />
                    </div>
                    <div className="chat-bubble">
                      {message.imagePreview ? (
                        <img
                          className="chat-image-preview"
                          src={message.imagePreview}
                          alt="Visual mood reference"
                        />
                      ) : null}
                      <p>{message.content}</p>
                      {message.result ? <AgentResult result={message.result} /> : null}
                    </div>
                  </article>
                ))}

                {agentState === "loading" ? (
                  <article className="chat-message chat-message-agent">
                    <div className="chat-avatar" aria-hidden="true">
                      <Icon name="waveform" />
                    </div>
                    <div className="chat-bubble">
                      <LoadingState
                        title="Listening and shaping the mix..."
                        text="Reading your intent, visual mood, and music direction."
                        rows={2}
                      />
                    </div>
                  </article>
                ) : null}
              </div>

              {agentError ? <ErrorBox message={agentError} /> : null}

              <div className="agent-example-row">
                {AGENT_EXAMPLES.map((example) => (
                  <button
                    className="example-chip"
                    key={example}
                    type="button"
                    onClick={() => handleAgentExample(example)}
                    disabled={agentState === "loading"}
                  >
                    {example}
                  </button>
                ))}
              </div>

              <form className="agent-compose" onSubmit={handleAgentSubmit}>
                <label>
                  Refine the Mix
                  <textarea
                    className="agent-textarea"
                    value={agentInput}
                    placeholder="Ask for a playlist, a mood, a photo BGM, or a follow-up change..."
                    disabled={agentState === "loading"}
                    onChange={(event) => setAgentInput(event.target.value)}
                  />
                </label>
                <div className="agent-attachment-row">
                  <label className="image-upload-button">
                    <Icon name="image" />
                    Add photo
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={agentState === "loading"}
                      onChange={(event) => {
                        handleAgentImageSelect(
                          event.currentTarget.files?.[0] ?? null,
                        );
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>
                  {agentImagePreview ? (
                    <div className="selected-image-preview">
                      <img src={agentImagePreview} alt="Selected visual mood" />
                      <div>
                        <span>Visual Mood</span>
                        <strong>{agentImage?.name ?? "Selected photo"}</strong>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleAgentImageSelect(null)}
                        disabled={agentState === "loading"}
                      >
                        Remove
                      </button>
                    </div>
                  ) : null}
                </div>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={
                    agentState === "loading" ||
                    (!agentInput.trim() && !agentImage)
                  }
                >
                  {agentState === "loading" ? (
                    <>
                      <span className="button-spinner" aria-hidden="true" />
                      Listening
                    </>
                  ) : (
                    <>
                      <Icon name="sparkles" />
                      Send to Agent
                    </>
                  )}
                </button>
              </form>
            </div>

            <ListeningIntentPanel
              preferences={agentPreferences}
              suggestions={agentSuggestions}
            />
          </div>
        </section>

        <section className="dashboard-section" id="dashboard">
          <SectionHeading
            eyebrow="Dashboard"
            title="Choose a music task"
            text="Start with a song, a mood, or a playlist idea."
          />

          <div className="feature-card-grid">
            <article className="feature-card">
              <span>01</span>
              <h3>Understand a Song</h3>
              <p>
                Upload a track and get a genre read, confidence bars, sound
                profile, and a DJ-style recommendation.
              </p>
            </article>
            <article className="feature-card">
              <span>02</span>
              <h3>Find Similar Music</h3>
              <p>
                Describe a mood, activity, or sonic direction and discover
                matching songs with clear listening cues.
              </p>
            </article>
            <article className="feature-card">
              <span>03</span>
              <h3>Plan a Playlist</h3>
              <p>
                Build a listening arc with stage timing, energy flow, and
                real song suggestions for each part of the session.
              </p>
            </article>
          </div>
        </section>

        <section className="studio-section" id="analyze-audio">
          <SectionHeading
            eyebrow="Audio Analysis"
            title="Understand a song"
            text="Upload a song to reveal its genre, sound profile, and listening direction."
          />

          <div className="workflow-grid">
            <form
              className="prompt-panel glass-card"
              onSubmit={handleAnalyze}
              aria-busy={analysisState === "loading"}
            >
              <label>
                Upload audio
                <span className="file-drop">
                  <span className="file-drop-button">Choose Audio</span>
                  <span className="file-drop-copy">
                    MP3, WAV, FLAC, M4A, AAC, OGG, WebM, AIFF, WMA, and more
                  </span>
                  <input
                    type="file"
                    accept="audio/*,.wav,.wave,.mp3,.flac,.m4a,.aac,.ogg,.oga,.opus,.webm,.wma,.aiff,.aif,.alac,.amr"
                    disabled={analysisState === "loading"}
                    onChange={(event) =>
                      setAudioFile(event.currentTarget.files?.[0] ?? null)
                    }
                  />
                </span>
              </label>

              {audioFile ? (
                <div className="file-preview">
                  <span>Selected song</span>
                  <strong>{audioFile.name}</strong>
                </div>
              ) : null}

              <button
                className="primary-button"
                type="submit"
                disabled={analysisState === "loading"}
              >
                {analysisState === "loading" ? (
                  <>
                    <span className="button-spinner" aria-hidden="true" />
                    Listening
                  </>
                ) : (
                  "Analyze Audio"
                )}
              </button>
            </form>

            <div className="results-panel glass-card">
              {analysisState === "loading" ? (
                <LoadingState
                  title="Listening and learning..."
                  text="Reading the song&apos;s shape, energy, and genre signals."
                />
              ) : analysisState === "error" ? (
                <ErrorBox message={analysisError} />
              ) : analysis ? (
                <div className="result-grid">
                  <div className="genre-hero">
                    <span>Closest genre</span>
                    <strong>{analysis.predicted_genre ?? "Unknown"}</strong>
                  </div>

                  <ProbabilityBars analysis={analysis} />

                  <div className="feature-grid">
                    <MetricCard
                      label="Tempo"
                      value={`${formatNumber(
                        analysis.features?.tempo_bpm,
                        0,
                      )} BPM`}
                      caption="Pace and movement"
                    />
                    <MetricCard
                      label="Energy"
                      value={formatNumber(analysis.features?.rms_mean, 3)}
                      caption={describeEnergy(analysis.features?.rms_mean)}
                    />
                    <MetricCard
                      label="Brightness"
                      value={formatNumber(
                        analysis.features?.centroid_mean,
                        0,
                      )}
                      caption={describeTone(analysis.features?.centroid_mean)}
                    />
                    <MetricCard
                      label="Texture"
                      value={formatNumber(analysis.features?.zcr_mean, 3)}
                      caption={describeTexture(analysis.features?.zcr_mean)}
                    />
                  </div>

                  <div className="recommendation-card">
                    <span className="eyebrow">Listening Interpretation</span>
                    <p>
                      {analysis.listening_interpretation ??
                        analysis.recommendation}
                    </p>
                  </div>

                  <SongRecommendationSection
                    eyebrow="Similar Mood"
                    title="Similar Real Songs"
                    songs={analyzedSongs}
                  />
                </div>
              ) : (
                <EmptyState
                  title="Start with a song."
                  text="Upload an audio file to see genre confidence, sound features, and a listening recommendation."
                />
              )}
            </div>
          </div>
        </section>

        <section className="studio-section" id="discover-music">
          <SectionHeading
            eyebrow="Music Discovery"
            title="Describe what you want to hear"
            text="Turn a mood, activity, or sound idea into real song recommendations."
          />

          <div className="workflow-grid">
            <form
              className="prompt-panel glass-card"
              onSubmit={handleRetrieve}
              aria-busy={retrievalState === "loading"}
            >
              <label>
                Music request
                <textarea
                  className="agent-textarea"
                  value={retrievalQuery}
                  placeholder="Describe the mood, activity, or sound you want..."
                  disabled={retrievalState === "loading"}
                  onChange={(event) => setRetrievalQuery(event.target.value)}
                />
              </label>

              <ExampleButtons
                examples={DISCOVERY_EXAMPLES}
                onSelect={setRetrievalQuery}
              />

              <button
                className="primary-button"
                type="submit"
                disabled={retrievalState === "loading"}
              >
                {retrievalState === "loading" ? (
                  <>
                    <span className="button-spinner" aria-hidden="true" />
                    Discovering
                  </>
                ) : (
                  "Discover Music"
                )}
              </button>
            </form>

            <div className="results-panel glass-card">
              {retrievalState === "loading" ? (
                <LoadingState
                  title="Finding the right sound..."
                  text="Listening for mood, pace, tone, and style."
                  rows={4}
                />
              ) : retrievalState === "error" ? (
                <ErrorBox message={retrievalError} />
              ) : retrieval ? (
                <div className="result-grid">
                  <TargetChips retrieval={retrieval} />

                  <p className="explanation">
                    {retrieval.listening_interpretation ??
                      "These songs match the mood, pace, tone, and style in your request."}
                  </p>

                  <SongRecommendationSection
                    eyebrow="Real Song Recommendations"
                    title="Recommended Songs"
                    songs={discoverySongs}
                  />

                  {(retrieval.results ?? []).length ? (
                    <EvidencePanel
                      title="Style signals behind the match"
                      text="Optional listening cues used to shape the recommendations."
                    >
                      <div className="track-grid">
                        {(retrieval.results ?? []).map((track, index) => (
                          <TrackCard
                            key={track.clip_id}
                            track={track}
                            index={index}
                          />
                        ))}
                      </div>
                    </EvidencePanel>
                  ) : null}
                </div>
              ) : (
                <EmptyState
                  title="Start by describing what you want to hear."
                  text="Use a mood, activity, genre, or listening moment to begin discovery."
                />
              )}
            </div>
          </div>
        </section>

        <section className="studio-section" id="playlist-planner">
          <SectionHeading
            eyebrow="Playlist Planner"
            title="Shape a listening journey"
            text="Describe the moment and build a playlist with timing, energy, and real song recommendations."
          />

          <div className="workflow-grid">
            <form
              className="prompt-panel glass-card"
              onSubmit={handlePlaylist}
              aria-busy={playlistState === "loading"}
            >
              <label>
                Playlist goal
                <textarea
                  className="agent-textarea"
                  value={playlistGoal}
                  placeholder="Describe the playlist you want, including activity and duration..."
                  disabled={playlistState === "loading"}
                  onChange={(event) => setPlaylistGoal(event.target.value)}
                />
              </label>

              <ExampleButtons
                examples={PLAYLIST_EXAMPLES}
                onSelect={setPlaylistGoal}
              />

              <div className="form-row">
                <label>
                  Total minutes
                  <input
                    className="input"
                    type="number"
                    min={1}
                    value={playlistMinutes}
                    disabled={playlistState === "loading"}
                    onChange={(event) =>
                      setPlaylistMinutes(Number(event.target.value))
                    }
                  />
                </label>
                <label>
                  Preferred styles
                  <input
                    className="input"
                    value={playlistGenres}
                    placeholder="rock, hip-hop"
                    disabled={playlistState === "loading"}
                    onChange={(event) => setPlaylistGenres(event.target.value)}
                  />
                </label>
              </div>

              <button
                className="primary-button"
                type="submit"
                disabled={playlistState === "loading"}
              >
                {playlistState === "loading" ? (
                  <>
                    <span className="button-spinner" aria-hidden="true" />
                    Planning
                  </>
                ) : (
                  "Plan Playlist"
                )}
              </button>
            </form>

            <div className="results-panel glass-card">
              {playlistState === "loading" ? (
                <LoadingState
                  title="Listening and planning..."
                  text="Building the arc, pacing the energy, and choosing songs."
                  rows={5}
                />
              ) : playlistState === "error" ? (
                <ErrorBox message={playlistError} />
              ) : playlist ? (
                <div className="result-grid">
                  <div className="playlist-summary-grid">
                    <MetricCard
                      label="Duration"
                      value={`${formatNumber(totalEstimatedMinutes, 0)} min`}
                      caption="Planned listening time"
                    />
                    <MetricCard
                      label="Stages"
                      value={formatNumber(playlist.stage_plan.length, 0)}
                      caption="Moments in the arc"
                    />
                    <MetricCard
                      label="Songs"
                      value={formatNumber(playlistSongCount, 0)}
                      caption="Real song suggestions"
                    />
                  </div>

                  <div className="recommendation-card">
                    <span className="eyebrow">How the playlist is structured</span>
                    <p>
                      {visiblePlaylistPlan?.explanation ??
                        "The listening arc is organized by time, mood, and energy for the session."}
                    </p>
                  </div>

                  {visiblePlaylistPlan ? (
                    <AgentPlaylistJourney plan={visiblePlaylistPlan} />
                  ) : null}

                  {Array.from(playlistByStage.entries()).length ? (
                    <EvidencePanel
                      title="Style signals behind the journey"
                      text="Optional listening cues used to support the playlist arc."
                    >
                      {Array.from(playlistByStage.entries()).map(
                        ([stage, tracks]) => (
                          <div className="stage-group" key={stage}>
                            <div className="stage-group-title">
                              <div>
                                <span className="eyebrow">Sound Evidence</span>
                                <h3>{stage}</h3>
                              </div>
                              <span className="soft-chip">
                                {tracks.length} cues
                              </span>
                            </div>
                            <div className="track-grid">
                              {tracks.map((track, index) => (
                                <TrackCard
                                  key={`${stage}-${track.clip_id}`}
                                  track={track}
                                  index={index}
                                />
                              ))}
                            </div>
                          </div>
                        ),
                      )}
                    </EvidencePanel>
                  ) : null}
                </div>
              ) : (
                <EmptyState
                  title="Start by describing what you want to hear."
                  text="Add an activity, mood, duration, and optional styles to create a playlist plan."
                />
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

