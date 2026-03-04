// ===== LP Creator SS - Settings Store =====
// Persists admin settings to a JSON file

import fs from 'fs';
import path from 'path';

export interface LPCreatorSettings {
  anthropicApiKey: string;   // API key (overrides env var if set)
  model: string;             // Claude model ID
  maxTokens: number;         // Max output tokens
}

const SETTINGS_DIR = path.join(__dirname, '..', '..', 'data');
const SETTINGS_FILE = path.join(SETTINGS_DIR, 'lp-creator-settings.json');

const DEFAULTS: LPCreatorSettings = {
  anthropicApiKey: '',
  model: 'claude-sonnet-4-5-20250929',
  maxTokens: 4096,
};

/** Load settings from file, falling back to defaults */
export function loadSettings(): LPCreatorSettings {
  try {
    if (fs.existsSync(SETTINGS_FILE)) {
      const raw = fs.readFileSync(SETTINGS_FILE, 'utf-8');
      const saved = JSON.parse(raw) as Partial<LPCreatorSettings>;
      return { ...DEFAULTS, ...saved };
    }
  } catch (err) {
    console.warn('[LP Creator] Failed to load settings, using defaults:', err);
  }
  return { ...DEFAULTS };
}

/** Save settings to file */
export function saveSettings(settings: Partial<LPCreatorSettings>): LPCreatorSettings {
  const current = loadSettings();
  const merged: LPCreatorSettings = { ...current, ...settings };

  // Ensure data directory exists
  if (!fs.existsSync(SETTINGS_DIR)) {
    fs.mkdirSync(SETTINGS_DIR, { recursive: true });
  }

  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(merged, null, 2), 'utf-8');
  return merged;
}

/** Get the effective API key (settings > env var) */
export function getEffectiveApiKey(): string | undefined {
  const settings = loadSettings();
  return settings.anthropicApiKey || process.env.ANTHROPIC_API_KEY || undefined;
}

/** Get the effective model */
export function getEffectiveModel(): string {
  const settings = loadSettings();
  return settings.model || process.env.CLAUDE_MODEL || DEFAULTS.model;
}

/** Get the effective max tokens */
export function getEffectiveMaxTokens(): number {
  const settings = loadSettings();
  return settings.maxTokens || DEFAULTS.maxTokens;
}
