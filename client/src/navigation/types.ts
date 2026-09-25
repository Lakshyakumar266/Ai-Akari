export type ScreenType = "characters" | "chat" | "stream" | "galary";

export interface NavigationState {
  screen: ScreenType;
  character: string;
}

export type ThemeMode = "dark" | "light";
