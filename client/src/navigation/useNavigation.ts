import { useState, useEffect, useCallback } from "react";
import type { ScreenType, NavigationState } from "./types";

const VALID_SCREENS: ScreenType[] = ["characters", "chat", "stream", "galary"];
const DEFAULT_SCREEN: ScreenType = "characters";
const DEFAULT_CHARACTER = "akari";

function parseLocation(): NavigationState {
  if (typeof window === "undefined") {
    return { screen: DEFAULT_SCREEN, character: DEFAULT_CHARACTER };
  }

  const params = new URLSearchParams(window.location.search);
  const rawScreen = params.get("screen")?.toLowerCase();
  const rawCharacter = params.get("character")?.toLowerCase();

  const screen: ScreenType = VALID_SCREENS.includes(rawScreen as ScreenType)
    ? (rawScreen as ScreenType)
    : DEFAULT_SCREEN;

  const character = rawCharacter && rawCharacter.trim().length > 0
    ? rawCharacter.trim()
    : DEFAULT_CHARACTER;

  return { screen, character };
}

function buildUrl(screen: ScreenType, character: string): string {
  return `/?screen=${screen}&character=${character}`;
}

export function useNavigation() {
  const [navState, setNavState] = useState<NavigationState>(parseLocation);

  // Synchronize URL on initial mount if missing or invalid
  useEffect(() => {
    const current = parseLocation();
    const params = new URLSearchParams(window.location.search);
    const hasScreen = params.has("screen");
    const hasChar = params.has("character");

    if (!hasScreen || !hasChar || !VALID_SCREENS.includes(params.get("screen") as ScreenType)) {
      const canonical = buildUrl(current.screen, current.character);
      window.history.replaceState(null, "", canonical);
    }
  }, []);

  // Handle browser back and forward navigation
  useEffect(() => {
    const handlePopState = () => {
      setNavState(parseLocation());
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  const navigate = useCallback((targetScreen: ScreenType, targetCharacter?: string) => {
    const char = targetCharacter || navState.character || DEFAULT_CHARACTER;
    const url = buildUrl(targetScreen, char);

    window.history.pushState(null, "", url);
    setNavState({ screen: targetScreen, character: char });
  }, [navState.character]);

  return {
    screen: navState.screen,
    character: navState.character,
    navigate,
  };
}
