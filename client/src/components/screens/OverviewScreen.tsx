import React, { useState, useEffect } from "react";
import {
  IconPencil,
  IconArrowRight,
  IconPlus,
  IconCamera,
  IconCheck,
} from "@tabler/icons-react";
import { avatarSocket, avatarEvents, type ConfigEvent } from "../../networking";
import "./OverviewScreen.css";

interface OverviewScreenProps {
  character: string;
  onStartChat: () => void;
  onOpenSettings?: () => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({
  character,
  onStartChat,
  onOpenSettings,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "voice">("overview");
  const [voiceEngine, setVoiceEngine] = useState<"fish" | "sovits">(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("akari_tts_engine");
      return stored === "sovits" ? "sovits" : "fish";
    }
    return "fish";
  });
  const [sovitsUrl, setSovitsUrl] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("akari_gpt_sovits_url") || "";
    }
    return "";
  });
  const [isUrlSaved, setIsUrlSaved] = useState<boolean>(false);

  // Sync state with live backend config broadcasts
  useEffect(() => {
    const unsubscribe = avatarEvents.subscribe("config", (event: ConfigEvent) => {
      if (event.tts_engine) {
        setVoiceEngine(event.tts_engine);
      }
      if (typeof event.sovits_url === "string") {
        setSovitsUrl(event.sovits_url);
      }
    });
    return unsubscribe;
  }, []);

  const handleSelectEngine = (engine: "fish" | "sovits") => {
    setVoiceEngine(engine);
    avatarSocket.setTtsEngine(engine);
  };

  const handleSaveSovitsUrl = () => {
    const trimmed = sovitsUrl.trim();
    avatarSocket.setSovitsUrl(trimmed);
    setIsUrlSaved(true);
    setTimeout(() => setIsUrlSaved(false), 2000);
  };

  const handleClearSovitsUrl = () => {
    setSovitsUrl("");
    avatarSocket.setSovitsUrl("");
  };

  const displayName = character.charAt(0).toUpperCase() + character.slice(1);
  const isSovitsConfigured = Boolean(sovitsUrl.trim());

  return (
    <div className="overview-screen-root" aria-label="Character Overview Screen">
      {/* ─── Left Character Information Panel ──────────────────────────────── */}
      <aside className="overview-info-panel" aria-label="Character Details">
        <div className="panel-header-section">
          <div className="panel-category-tag">
            <span>CHARACTERS</span>
            <span>01</span>
          </div>
          <h1 className="panel-character-name">{displayName}</h1>
          <div className="panel-character-subtitle">Tsundere · Lively</div>
        </div>

        <div className="panel-action-row">
          <button
            type="button"
            className="panel-edit-btn"
            title="Edit character profile"
            onClick={() => { }}
          >
            <IconPencil size={15} stroke={1.8} />
            <span>Edit character</span>
          </button>
          <button
            type="button"
            className="panel-icon-btn"
            title="Delete character"
            onClick={() => { }}
          >
            <IconCamera size={16} stroke={1.8} />
          </button>
        </div>

        {/* Overview / Voice tabs */}
        <div className="panel-tabs-row" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "overview"}
            className={`panel-tab ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "voice"}
            className={`panel-tab ${activeTab === "voice" ? "active" : ""}`}
            onClick={() => setActiveTab("voice")}
          >
            Voice
          </button>
        </div>

        {/* Personality & model link -> takes user to Settings page */}
        <div
          className="panel-nav-row"
          onClick={onOpenSettings}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && onOpenSettings?.()}
          title="Open Settings to configure Personality & AI Model"
        >
          <span>Personality & model</span>
          <IconArrowRight size={14} stroke={2} />
        </div>


        {/* Voice engine configuration (Voice Tab) */}
        {activeTab === "voice" && (
          <div className="panel-voice-section">
            <div className="panel-voice-header">
              <span className="panel-voice-title">Audio Pipeline</span>
              <span
                className="panel-voice-config"
                onClick={onOpenSettings}
                title="Configure advanced audio settings"
              >
                Configure
              </span>
            </div>

            <div className="panel-voice-toggles">
              <button
                type="button"
                className={`panel-voice-toggle-btn ${voiceEngine === "fish" ? "active" : ""}`}
                onClick={() => handleSelectEngine("fish")}
                title="Use Fish Audio cloud voice pipeline"
              >
                Fish Audio
              </button>
              <button
                type="button"
                className={`panel-voice-toggle-btn ${voiceEngine === "sovits" ? "active" : ""}`}
                onClick={() => handleSelectEngine("sovits")}
                title="Use GPT-SoVITS public or local server instance"
              >
                GPT-SoVITS
              </button>
            </div>

            <p className="panel-voice-caption">
              {voiceEngine === "fish"
                ? "Fish Audio: Voice synthesized via cloud Fish Audio pipeline."
                : "GPT-SoVITS: Voice synthesized via public or local GPT-SoVITS server."}
            </p>

            {/* GPT-SoVITS Connection Details Card */}
            {voiceEngine === "sovits" && (
              <div className="panel-sovits-config-card">
                <div className="sovits-field-header">
                  <span className="sovits-field-label">Connection URL</span>
                  <span className={`sovits-status-tag ${isSovitsConfigured ? "ready" : "needed"}`}>
                    <span className="sovits-status-dot" />
                    <span>{isSovitsConfigured ? "Connected" : "URL Needed"}</span>
                  </span>
                </div>

                <div className="sovits-input-row">
                  <input
                    type="url"
                    className="sovits-url-input"
                    placeholder="http://127.0.0.1:9880 or https://..."
                    value={sovitsUrl}
                    onChange={(e) => setSovitsUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSaveSovitsUrl()}
                    spellCheck={false}
                    aria-label="GPT-SoVITS Server URL"
                  />
                </div>

                <div className="sovits-actions-row">
                  <button
                    type="button"
                    className={`sovits-save-btn ${isUrlSaved ? "saved" : ""}`}
                    onClick={handleSaveSovitsUrl}
                  >
                    {isUrlSaved ? (
                      <>
                        <IconCheck size={13} stroke={2.5} />
                        <span>Saved</span>
                      </>
                    ) : (
                      <span>Save & Connect</span>
                    )}
                  </button>
                  {sovitsUrl && (
                    <button
                      type="button"
                      className="sovits-clear-btn"
                      onClick={handleClearSovitsUrl}
                      title="Clear configured URL"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Fish Audio Active Info */}
            {voiceEngine === "fish" && (
              <div className="panel-fish-info-box">
                <div className="fish-status-line">
                  <span className="sovits-status-dot ready" />
                  <span>Cloud Engine Active</span>
                </div>
                <span className="fish-model-note">Preset: <code>s2.1-pro-free</code></span>
              </div>
            )}
          </div>
        )}

        {/* Primary CTA */}
        <button
          type="button"
          className="panel-start-chat-btn"
          onClick={onStartChat}
        >
          <span>Start chat</span>
          <IconArrowRight size={16} stroke={2.5} />
        </button>
      </aside>

      {/* ─── Bottom Character Selector Row ─────────────────────────────────── */}
      <div className="overview-bottom-selector" aria-label="Character Selector">
        <div className="selector-cards-row">
          <div className="selector-card-wrapper">
            <div className="selector-card selected">
              <img
                src="/akari_avatar.jpg"
                alt="Akari Watanabe"
                className="selector-card-img"
              />
            </div>
            <span className="selector-card-name">{displayName}</span>
          </div>
        </div>

        <button
          type="button"
          className="selector-add-btn"
          title="Add a new character"
        >
          <IconPlus size={14} stroke={2} />
          <span>Add character</span>
        </button>
      </div>
    </div>
  );
};
