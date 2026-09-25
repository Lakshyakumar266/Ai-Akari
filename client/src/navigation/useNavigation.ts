import { useState, useEffect, useCallback } from "react";
import type { ScreenType, NavigationState } from "./types";
import { avatarSocket } from "../networking/AvatarSocket";

const VALID_SCREENS: ScreenType[] = ["characters", "chat", "stream", "galary", "settings"];
const DEFAULT_SCREEN: ScreenType = "characters";
const DEFAULT_CHARACTER = "akari";
const DEFAULT_PROVIDER = "mistral";
const DEFAULT_MODEL = "ministral-8b-latest";

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
    };
  }

  const params = new URLSearchParams(window.location.search);
  const rawScreen = params.get("screen")?.toLowerCase();
  const rawCharacter = params.get("character")?.toLowerCase();
  const rawProvider = params.get("provider")?.toLowerCase();
  const rawModel = params.get("model");

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

  return { screen, character, provider, model };
}

function buildUrl(
  screen: ScreenType,
  character: string,
  provider: string,
  model: string
): string {
  const params = new URLSearchParams();
  params.set("screen", screen);
  params.set("character", character);
  params.set("provider", provider);
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
    const hasProvider = params.has("provider");
    const hasModel = params.has("model");

    if (!hasScreen || !hasChar || !hasProvider || !hasModel || !VALID_SCREENS.includes(params.get("screen") as ScreenType)) {
      const canonical = buildUrl(current.screen, current.character, current.provider, current.model);
      window.history.replaceState(null, "", canonical);
    }

    avatarSocket.setLlmProvider(current.provider, current.model);
  }, []);

  // Handle browser back and forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const updated = parseLocation();
      setNavState(updated);
      avatarSocket.setLlmProvider(updated.provider, updated.model);
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
    targetModel?: string
  ) => {
    const char = targetCharacter || navState.character || DEFAULT_CHARACTER;
    const prov = targetProvider || navState.provider || DEFAULT_PROVIDER;
    const mod = targetModel || navState.model || getDefaultModelForProvider(prov);
    const url = buildUrl(targetScreen, char, prov, mod);

    window.history.pushState(null, "", url);
    setNavState({ screen: targetScreen, character: char, provider: prov, model: mod });
  }, [navState.character, navState.provider, navState.model]);

  const updateLlm = useCallback((newProvider: string, newModel?: string) => {
    const prov = newProvider;
    const mod = newModel || getDefaultModelForProvider(prov);
    const url = buildUrl(navState.screen, navState.character, prov, mod);

    localStorage.setItem("akari_llm_provider", prov);
    localStorage.setItem("akari_llm_model", mod);
    window.history.replaceState(null, "", url);
    setNavState(prev => ({ ...prev, provider: prov, model: mod }));
    avatarSocket.setLlmProvider(prov, mod);
  }, [navState.screen, navState.character]);

  return {
    screen: navState.screen,
    character: navState.character,
    provider: navState.provider,
    model: navState.model,
    navigate,
    updateLlm,
  };
}
