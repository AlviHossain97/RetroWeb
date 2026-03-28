export const NVIDIA_BASE = "/api/nvidia";
export const KOKORO_BASE = "/api/kokoro";
export const STT_BASE = "/api/whisper";
export const PISTATION_API = "/api/pistation";

export const NVIDIA_MODELS = [
  "moonshotai/kimi-k2-thinking",
  "mistralai/mistral-large-3-675b-instruct-2512",
  "stepfun-ai/step-3.5-flash",
  "deepseek-ai/deepseek-v3.2",
  "z-ai/glm4.7",
];

export const MODEL_ICONS: Record<string, { icon: string; label: string }> = {
  "moonshotai/kimi-k2-thinking": { icon: "/model-icons/moonshot.jpeg", label: "Kimi K2 Thinking" },
  "mistralai/mistral-large-3-675b-instruct-2512": { icon: "/model-icons/mistral.png", label: "Mistral Large 3 675B" },
  "stepfun-ai/step-3.5-flash": { icon: "/model-icons/stepfun.jpeg", label: "Step 3.5 Flash" },
  "deepseek-ai/deepseek-v3.2": { icon: "/model-icons/deepseek.jpg", label: "DeepSeek V3.2" },
  "z-ai/glm4.7": { icon: "/model-icons/zhipu.png", label: "GLM 4.7" },
};

export const SENTENCE_END = /[.!?]\s*$/;
export const CLAUSE_END = /[,;:\u2014\u2013]\s*$/;

export const DEFAULT_MODEL = "deepseek-ai/deepseek-v3.2";

export interface Message {
  role: "user" | "assistant";
  content: string;
  images?: string[];
  grounded?: boolean;
  sources?: { id: number; title: string; url: string; snippet: string }[];
}

export type ConvState = "idle" | "streaming" | "error";
export type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error";
export type OverlayState = "none" | "modelPicker" | "overflowMenu" | "voiceSettings" | "clearConfirm";

export const QUICK_ACTIONS = [
  {
    icon: "\ud83d\udcca",
    label: "My Stats",
    prompt: "What are my gaming stats? Give me a summary of my total playtime, most played games, and favorite systems.",
  },
  {
    icon: "\ud83c\udfb2",
    label: "Recommend",
    prompt: "Based on my gaming history and play patterns, what retro game should I play next? Give me 3 recommendations with brief reasons.",
  },
  {
    icon: "\ud83c\udfaf",
    label: "Quiz",
    prompt: "Give me a fun retro gaming trivia question! Make it multiple choice (A/B/C/D) and don't reveal the answer until I guess. Pick from any classic game or console.",
  },
  {
    icon: "\ud83c\udfc6",
    label: "Records",
    prompt: "What's my longest gaming session ever? And which game have I spent the most time on?",
  },
];
