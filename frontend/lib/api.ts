export const API_BASE = "http://127.0.0.1:8000";

export class ApiRequestError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.body = body;
  }
}

export type TopPrediction = {
  genre: string;
  probability: number;
};

export type AnalyzeResponse = {
  status: string;
  predicted_genre?: string;
  top3?: TopPrediction[];
  features?: Record<string, number>;
  recommendation?: string;
  listening_interpretation?: string;
  similar_songs?: AgentSong[];
  recommended_songs?: AgentSong[];
};

export type RetrievalTrack = {
  clip_id: string;
  genre: string;
  audio_path: string;
  tempo_bpm: number;
  rms_mean: number;
  centroid_mean: number;
  final_score: number;
};

export type RetrieveResponse = {
  status: string;
  parsed_targets?: {
    tempo_bpm?: number;
    rms_mean?: number;
    centroid_mean?: number;
    preferred_genres?: string[];
    explanation?: string;
  };
  results?: RetrievalTrack[];
  explanation?: string;
  listening_interpretation?: string;
  recommended_songs?: AgentSong[];
};

export type PlaylistStage = {
  stage: string;
  minutes: number;
  tempo_hint?: string;
  energy_hint?: string;
};

export type PlaylistTrack = RetrievalTrack & {
  stage: string;
  minutes_allocated: number;
};

export type PlaylistResponse = {
  status: string;
  stage_plan: PlaylistStage[];
  playlist: PlaylistTrack[];
  explanation: string;
  total_estimated_minutes?: number;
  playlist_plan?: AgentPlaylistPlan | null;
  recommended_songs?: AgentSong[];
};

export type AgentSong = {
  title: string;
  artist: string;
  reason: string;
  stage?: string | null;
  genre?: string | null;
  mood?: string | null;
  energy?: string | null;
  use_case?: string | null;
  spotify_url?: string | null;
  netease_url?: string | null;
  verification?: string | null;
};

export type VisualProfile = {
  scene_summary?: string;
  visual_mood?: string;
  color_palette?: string[];
  energy_level?: string;
  aesthetic_tags?: string[];
  recommended_music_direction?: string;
  short_video_bgm_direction?: string;
};

export type AgentPlaylistStage = {
  stage: string;
  minutes: number;
  time_range?: {
    start: number;
    end: number;
  };
  intended_mood?: string;
  energy_level?: string;
  recommended_songs?: AgentSong[];
};

export type AgentPlaylistPlan = {
  stages: AgentPlaylistStage[];
  recommended_songs?: AgentSong[];
  explanation?: string;
};

export type AgentPreferences = {
  previous_user_request?: string;
  current_goal?: string;
  preferred_styles?: string[];
  disliked_styles?: string[];
  duration?: number;
  energy_direction?: string;
  last_action?: string;
  stage_plan?: PlaylistStage[];
  audio_context?: AnalyzeResponse;
  last_visual_profile?: VisualProfile | null;
  visual_profile?: VisualProfile | null;
};

export type AgentResponse = {
  answer_text: string;
  detected_intent: string;
  recommended_songs: AgentSong[];
  playlist_plan?: AgentPlaylistPlan | null;
  visual_profile?: VisualProfile | null;
  updated_preferences: AgentPreferences;
  follow_up_suggestions: string[];
};

export type LlmProviderName = "openai" | "deepseek" | "qwen" | "offline";

export type LlmProviderStatus = {
  provider: LlmProviderName;
  model: string;
  vision_model: string;
  configured: boolean;
  capabilities: {
    supports_text: boolean;
    supports_vision: boolean;
    supports_web_search: boolean;
    supports_json_output: boolean;
  };
};

async function parseResponseBody(response: Response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function errorMessageFromBody(body: unknown, status: number) {
  if (typeof body === "string" && body.trim()) {
    return body;
  }

  if (body && typeof body === "object") {
    const value = body as {
      detail?: string | Array<{ msg?: string }>;
      message?: string;
    };

    if (typeof value.detail === "string") {
      return value.detail;
    }

    if (Array.isArray(value.detail) && value.detail[0]?.msg) {
      return value.detail[0].msg;
    }

    if (typeof value.message === "string") {
      return value.message;
    }
  }

  return `Request failed with ${status}`;
}

async function readJson<T>(
  response: Response,
  requestType: string,
): Promise<T> {
  const body = await parseResponseBody(response);

  if (!response.ok) {
    console.error(`${requestType} request failed`, {
      status: response.status,
      responseText: typeof body === "string" ? body : JSON.stringify(body),
    });

    throw new ApiRequestError(
      errorMessageFromBody(body, response.status),
      response.status,
      body,
    );
  }

  return body as T;
}

export async function analyzeAudio(file: File): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;

  try {
    response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      body: formData,
    });
  } catch (error) {
    console.error("Analyze Audio request could not be completed", error);
    throw error;
  }

  return readJson<AnalyzeResponse>(response, "Analyze Audio");
}

export async function retrieveTracks(
  query: string,
  topK = 6,
): Promise<RetrieveResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
    });
  } catch (error) {
    console.error("Discover Music request could not be completed", error);
    throw error;
  }

  return readJson<RetrieveResponse>(response, "Discover Music");
}

export async function planPlaylist(payload: {
  goal: string;
  total_minutes: number;
  top_k_per_stage: number;
  preferred_genres: string[] | null;
  custom_plan?: Array<Record<string, unknown>>;
}): Promise<PlaylistResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}/playlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.error("Playlist Planner request could not be completed", error);
    throw error;
  }

  return readJson<PlaylistResponse>(response, "Playlist Planner");
}

export async function sendAgentMessage(
  message: string,
  context: AgentPreferences,
): Promise<AgentResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}/agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context }),
    });
  } catch (error) {
    console.error("Agent Studio request could not be completed", error);
    throw error;
  }

  return readJson<AgentResponse>(response, "Agent Studio");
}

export async function sendAgentImageMessage(
  message: string,
  image: File,
  context: AgentPreferences,
): Promise<AgentResponse> {
  const formData = new FormData();
  formData.append("message", message);
  formData.append("context", JSON.stringify(context));
  formData.append("image", image);

  let response: Response;

  try {
    response = await fetch(`${API_BASE}/agent/image`, {
      method: "POST",
      body: formData,
    });
  } catch (error) {
    console.error("Agent Studio image request could not be completed", error);
    throw error;
  }

  return readJson<AgentResponse>(response, "Agent Studio Image");
}

export async function getLlmProviderStatus(): Promise<LlmProviderStatus> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}/settings/llm`);
  } catch (error) {
    console.error("Advanced settings request could not be completed", error);
    throw error;
  }

  return readJson<LlmProviderStatus>(response, "Advanced Settings");
}

export async function setLlmProvider(
  provider: LlmProviderName,
): Promise<LlmProviderStatus> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}/settings/llm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider }),
    });
  } catch (error) {
    console.error("Advanced settings update could not be completed", error);
    throw error;
  }

  return readJson<LlmProviderStatus>(response, "Advanced Settings");
}
