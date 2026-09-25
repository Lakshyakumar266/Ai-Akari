import React from "react";
import {
  IconMenu2,
  IconSun,
  IconMoon,
  IconUserSquareRounded,
  IconMessageCircle,
  IconCube,
  IconCamera,
} from "@tabler/icons-react";
import type { ScreenType } from "./types";
import { useTheme } from "./ThemeContext";
import "./Sidebar.css";

interface SidebarProps {
  currentScreen: ScreenType;
  currentCharacter: string;
  onNavigate: (screen: ScreenType) => void;
  isOpen?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  isOpen = true,
  onToggleCollapse,
}) => {
  const { theme, setTheme } = useTheme();

  return (
    <aside className={`app-sidebar ${!isOpen ? "collapsed" : ""}`} aria-label="Application Sidebar">
      <div className="sidebar-top">
        <button
          type="button"
          className="sidebar-menu-btn"
          aria-label="Hide Sidebar"
          title="Hide Sidebar"
          onClick={onToggleCollapse}
        >
          <IconMenu2 size={19} stroke={1.8} />
        </button>

        <nav className="sidebar-nav-list" aria-label="Main Navigation">
          {/* 1. Characters / Overview */}
          <button
            type="button"
            className={`sidebar-nav-item ${currentScreen === "characters" ? "active" : ""}`}
            onClick={() => onNavigate("characters")}
            title="Characters / Overview"
            aria-label="Characters / Overview"
          >
            <IconUserSquareRounded size={19} stroke={1.7} />
          </button>

          {/* 2. Chat */}
          <button
            type="button"
            className={`sidebar-nav-item ${currentScreen === "chat" ? "active" : ""}`}
            onClick={() => onNavigate("chat")}
            title="Chat"
            aria-label="Chat"
          >
            <IconMessageCircle size={19} stroke={1.7} />
          </button>

          {/* 3. OpenSpace / Stream */}
          <button
            type="button"
            className={`sidebar-nav-item ${currentScreen === "stream" ? "active" : ""}`}
            onClick={() => onNavigate("stream")}
            title="OpenSpace / Stream"
            aria-label="OpenSpace / Stream"
          >
            <IconCube size={19} stroke={1.7} />
          </button>

          {/* 4. Gallery */}
          <button
            type="button"
            className={`sidebar-nav-item ${currentScreen === "galary" ? "active" : ""}`}
            onClick={() => onNavigate("galary")}
            title="Gallery"
            aria-label="Gallery"
          >
            <IconCamera size={19} stroke={1.7} />
          </button>
        </nav>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-theme-group" role="group" aria-label="Theme mode switcher">
          {/* Sun icon for light theme */}
          <button
            type="button"
            className={`sidebar-theme-btn ${theme === "light" ? "active" : ""}`}
            onClick={() => setTheme("light")}
            title="Light mode"
            aria-label="Switch to light mode"
          >
            <IconSun size={16} stroke={1.8} />
          </button>

          {/* Moon icon for dark theme */}
          <button
            type="button"
            className={`sidebar-theme-btn ${theme === "dark" ? "active" : ""}`}
            onClick={() => setTheme("dark")}
            title="Dark mode"
            aria-label="Switch to dark mode"
          >
            <IconMoon size={16} stroke={1.8} />
          </button>
        </div>
      </div>
    </aside>
  );
};
