import { useState, useEffect, useCallback } from "react";
import type { ScreenType, NavigationState } from "./types";
import { avatarSocket } from "../networking/AvatarSocket";

const VALID_SCREENS: ScreenType[] = ["characters", "chat", "stream", "galary", "settings"];
const DEFAULT_SCREEN: ScreenType = "characters";
const DEFAULT_CHARACTER = "akari";
const DEFAULT_PROVIDER = "mistral";
const DEFAULT_MODEL = "ministral-8b-latest";
const DEFAULT_TOOLS = true;

function getDefaultModelForProvider(provider: string): string {
  return provider === "freeai" ? "qwen7b" : "ministral-8b-latest";
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
  const rawProvider = params.get("provider")?.toLowerCase();
  const rawModel = params.get("model");
  const rawTools = params.get("tools");

  const screen: ScreenType = VALID_SCREENS.includes(rawScreen as ScreenType)
    ? (rawScreen as ScreenType)
    : DEFAULT_SCREEN;

  const character = rawCharacter && rawCharacter.trim().length > 0
    ? rawCharacter.trim()
    : DEFAULT_CHARACTER;

  const provider = rawProvider && (rawProvider === "freeai" || rawProvider === "mistral")
    ? rawProvider
    : (localStorage.getItem("akari_llm_provider") || DEFAULT_PROVIDER);

  const model = rawModel && rawModel.trim().length > 0
    ? rawModel.trim()
    : (localStorage.getItem("akari_llm_model") || getDefaultModelForProvider(provider));

  const storedTools = localStorage.getItem("akari_tool_calling_enabled");
  const tools = rawTools !== null
    ? rawTools === "true"
    : (storedTools !== null ? storedTools === "true" : DEFAULT_TOOLS);

  return { screen, character, provider, model, tools };
}

function buildUrl(
  screen: ScreenType,
  character: string,
  provider: string,
  model: string,
  tools: boolean
): string {
  const params = new URLSearchParams();
  params.set("screen", screen);
  params.set("character", character);
  params.set("provider", provider);
  params.set("model", model);
  params.set("tools", tools ? "true" : "false");
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
    const hasProvider = params.has("provider");
    const hasModel = params.has("model");
    const hasTools = params.has("tools");

    if (
      !hasScreen ||
      !hasChar ||
      !hasProvider ||
      !hasModel ||
      !hasTools ||
      !VALID_SCREENS.includes(params.get("screen") as ScreenType)
    ) {
      const canonical = buildUrl(
        current.screen,
        current.character,
        current.provider,
        current.model,
        current.tools
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
    const prov = targetProvider || navState.provider || DEFAULT_PROVIDER;
    const mod = targetModel || navState.model || getDefaultModelForProvider(prov);
    const tls = targetTools !== undefined ? targetTools : navState.tools;
    const url = buildUrl(targetScreen, char, prov, mod, tls);

    window.history.pushState(null, "", url);
    setNavState({ screen: targetScreen, character: char, provider: prov, model: mod, tools: tls });
  }, [navState.character, navState.provider, navState.model, navState.tools]);

  const updateLlm = useCallback((newProvider: string, newModel?: string) => {
    const prov = newProvider;
    const mod = newModel || getDefaultModelForProvider(prov);
    const tls = navState.tools;
    const url = buildUrl(navState.screen, navState.character, prov, mod, tls);

    localStorage.setItem("akari_llm_provider", prov);
    localStorage.setItem("akari_llm_model", mod);
    window.history.replaceState(null, "", url);
    setNavState(prev => ({ ...prev, provider: prov, model: mod }));
    avatarSocket.setLlmProvider(prov, mod);
  }, [navState.screen, navState.character, navState.tools]);

  const updateToolCalling = useCallback((enabled: boolean) => {
    const url = buildUrl(
      navState.screen,
      navState.character,
      navState.provider,
      navState.model,
      enabled
    );
    localStorage.setItem("akari_tool_calling_enabled", enabled ? "true" : "false");
    window.history.replaceState(null, "", url);
    setNavState(prev => ({ ...prev, tools: enabled }));
    avatarSocket.setToolCalling(enabled);
  }, [navState.screen, navState.character, navState.provider, navState.model]);

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

