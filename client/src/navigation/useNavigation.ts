import { useState, useEffect, useCallback } from "react";
import type { ScreenType, NavigationState } from "./types";
import { avatarSocket } from "../networking/AvatarSocket";

const VALID_SCREENS: ScreenType[] = ["characters", "chat", "stream", "galary", "settings"];
const DEFAULT_SCREEN: ScreenType = "characters";
const DEFAULT_CHARACTER = "akari";
const DEFAULT_PROVIDER = "mistral";
const DEFAULT_MODEL = "ministral-8b-latest";
const DEFAULT_TOOLS = true;

export function getDefaultModelForProvider(provider: string): string {
  if (provider === "openai") return "gpt-4o-mini";
  if (provider === "freeai") return "qwen7b";
  if (provider === "openrouter") return "openrouter/free";
  if (provider === "bedrock") return "mistral.ministral-3-8b-instruct";
  return "ministral-8b-latest";
}

export function getProviderForModel(model: string, fallbackProvider?: string): string {
  if (!model) return fallbackProvider || DEFAULT_PROVIDER;
  const lower = model.toLowerCase();
  if (
    lower.startsWith("openai.") ||
    lower.includes("gpt-6") ||
    lower.includes("gpt-5.5") ||
    lower.includes("luna") ||
    lower.includes("gpt-oss") ||
    lower.startsWith("mistral.ministral-3") ||
    lower.includes("gemma") ||
    lower.startsWith("qwen.qwen3-32b") ||
    lower.startsWith("deepseek.v3") ||
    lower.startsWith("mistral.mistral-large-3") ||
    lower.startsWith("anthropic.claude-sonnet-5") ||
    lower.startsWith("anthropic.claude-opus-5") ||
    lower.startsWith("bedrock")
  ) {
    return "bedrock";
  }
  if (
    lower.startsWith("gpt-") ||
    lower.startsWith("o1") ||
    lower.startsWith("o3") ||
    lower.startsWith("chatgpt")
  ) {
    return "openai";
  }
  if (lower.includes("/") || lower.startsWith("openrouter")) {
    return "openrouter";
  }
  if (lower === "qwen7b" || lower.startsWith("freeai")) {
    return "freeai";
  }
  if (
    lower.startsWith("ministral") ||
    lower.startsWith("mistral") ||
    lower.startsWith("pixtral") ||
    lower.startsWith("open-mistral")
  ) {
    return "mistral";
  }
  return fallbackProvider || DEFAULT_PROVIDER;
}

function parseLocation(): NavigationState {
  if (typeof window === "undefined") {
    return {
      screen: DEFAULT_SCREEN,
      character: DEFAULT_CHARACTER,
      provider: DEFAULT_PROVIDER,
      model: DEFAULT_MODEL,
      tools: DEFAULT_TOOLS,
    };
  }

  const params = new URLSearchParams(window.location.search);
  const rawScreen = params.get("screen")?.toLowerCase();
  const rawCharacter = params.get("character")?.toLowerCase();
  const rawModel = params.get("model");

  const screen: ScreenType = VALID_SCREENS.includes(rawScreen as ScreenType)
    ? (rawScreen as ScreenType)
    : DEFAULT_SCREEN;

  const character = rawCharacter && rawCharacter.trim().length > 0
    ? rawCharacter.trim()
    : DEFAULT_CHARACTER;

  // Tool calling setting is strictly stored in localStorage (no tools in URL)
  const storedTools = localStorage.getItem("akari_tool_calling_enabled");
  const tools = storedTools !== null ? storedTools === "true" : DEFAULT_TOOLS;

  // Stored preferences
  const storedProvider = localStorage.getItem("akari_llm_provider");
  const storedModel = localStorage.getItem("akari_llm_model");

  let model: string;
  let provider: string;

  if (rawModel && rawModel.trim().length > 0) {
    model = rawModel.trim();
    // Infer provider from the explicit model in the URL, falling back to stored provider
    provider = getProviderForModel(model, storedProvider || undefined);
  } else if (storedModel && storedModel.trim().length > 0) {
    model = storedModel.trim();
    provider = storedProvider || getProviderForModel(model);
  } else {
    provider = storedProvider || DEFAULT_PROVIDER;
    model = getDefaultModelForProvider(provider);
  }

  return { screen, character, provider, model, tools };
}

function buildUrl(
  screen: ScreenType,
  character: string,
  model: string
): string {
  const params = new URLSearchParams();
  params.set("screen", screen);
  params.set("character", character);
  params.set("model", model);
  return `/?${params.toString()}`;
}

export function useNavigation() {
  const [navState, setNavState] = useState<NavigationState>(parseLocation);

  // Synchronize URL and backend on initial mount
  useEffect(() => {
    const current = parseLocation();
    const params = new URLSearchParams(window.location.search);
    const hasScreen = params.has("screen");
    const hasChar = params.has("character");
    const hasModel = params.has("model");
    const hasLegacyProvider = params.has("provider");
    const hasLegacyTools = params.has("tools");

    // Enforce clean URL: only screen, character, and model in query parameters
    if (
      !hasScreen ||
      !hasChar ||
      !hasModel ||
      hasLegacyProvider ||
      hasLegacyTools ||
      !VALID_SCREENS.includes(params.get("screen") as ScreenType)
    ) {
      const canonical = buildUrl(
        current.screen,
        current.character,
        current.model
      );
      window.history.replaceState(null, "", canonical);
    }

    avatarSocket.setLlmProvider(current.provider, current.model);
    avatarSocket.setToolCalling(current.tools);
  }, []);

  // Handle browser back and forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const updated = parseLocation();
      setNavState(updated);
      avatarSocket.setLlmProvider(updated.provider, updated.model);
      avatarSocket.setToolCalling(updated.tools);
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  const navigate = useCallback((
    targetScreen: ScreenType,
    targetCharacter?: string,
    targetProvider?: string,
    targetModel?: string,
    targetTools?: boolean
  ) => {
    const char = targetCharacter || navState.character || DEFAULT_CHARACTER;
    const prov =
      targetProvider ||
      (targetModel ? getProviderForModel(targetModel, navState.provider) : navState.provider) ||
      DEFAULT_PROVIDER;
    const mod = targetModel || navState.model || getDefaultModelForProvider(prov);
    const tls = targetTools !== undefined ? targetTools : navState.tools;
    const url = buildUrl(targetScreen, char, mod);

    if (targetProvider) {
      localStorage.setItem("akari_llm_provider", prov);
    }
    if (targetModel) {
      localStorage.setItem("akari_llm_model", mod);
    }
    if (targetTools !== undefined) {
      localStorage.setItem("akari_tool_calling_enabled", tls ? "true" : "false");
    }

    window.history.pushState(null, "", url);
    setNavState({ screen: targetScreen, character: char, provider: prov, model: mod, tools: tls });
  }, [navState.character, navState.provider, navState.model, navState.tools]);

  const updateLlm = useCallback((newProvider: string, newModel?: string) => {
    const prov = newProvider;
    const mod = newModel || getDefaultModelForProvider(prov);
    const url = buildUrl(navState.screen, navState.character, mod);

    localStorage.setItem("akari_llm_provider", prov);
    localStorage.setItem("akari_llm_model", mod);
    window.history.replaceState(null, "", url);
    setNavState(prev => ({ ...prev, provider: prov, model: mod }));
    avatarSocket.setLlmProvider(prov, mod);
  }, [navState.screen, navState.character]);

  const updateToolCalling = useCallback((enabled: boolean) => {
    // Tool calling is saved exclusively in localStorage and not shown in the URL
    localStorage.setItem("akari_tool_calling_enabled", enabled ? "true" : "false");
    setNavState(prev => ({ ...prev, tools: enabled }));
    avatarSocket.setToolCalling(enabled);
  }, []);

  return {
    screen: navState.screen,
    character: navState.character,
    provider: navState.provider,
    model: navState.model,
    tools: navState.tools,
    navigate,
    updateLlm,
    updateToolCalling,
  };
}

