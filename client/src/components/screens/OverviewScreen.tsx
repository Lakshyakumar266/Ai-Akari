import React, { useState } from "react";
import {
  IconPencil,
  IconTrash,
  IconArrowRight,
  IconPlus,
  IconCamera,
} from "@tabler/icons-react";
import "./OverviewScreen.css";

interface OverviewScreenProps {
  character: string;
  onStartChat: () => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({
  character,
  onStartChat,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "voice">("overview");
  const [voiceEngine, setVoiceEngine] = useState<"fish" | "sovits">("fish");

  const displayName = character.charAt(0).toUpperCase() + character.slice(1);

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
            onClick={() => {}}
          >
            <IconPencil size={15} stroke={1.8} />
            <span>Edit character</span>
          </button>
          <button
            type="button"
            className="panel-icon-btn"
            title="Delete character"
            onClick={() => {}}
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

        {/* Personality & model link */}
        <div className="panel-nav-row" onClick={() => {}}>
          <span>Personality & model</span>
          <IconArrowRight size={14} stroke={2} />
        </div>

        {/* Voice engine configuration */}
        <div className="panel-voice-section">
          <div className="panel-voice-header">
            <span className="panel-voice-title">Voice</span>
            <span className="panel-voice-config">Configure</span>
          </div>

          <div className="panel-voice-toggles">
            <button
              type="button"
              className={`panel-voice-toggle-btn ${voiceEngine === "fish" ? "active" : ""}`}
              onClick={() => setVoiceEngine("fish")}
            >
              Fish Audio
            </button>
            <button
              type="button"
              className={`panel-voice-toggle-btn ${voiceEngine === "sovits" ? "active" : ""}`}
              onClick={() => setVoiceEngine("sovits")}
            >
              GPT-SoVITS
            </button>
          </div>

          <p className="panel-voice-caption">
            {voiceEngine === "fish"
              ? "Fish Audio: Voice synthesized via Fish Audio pipeline."
              : "GPT-SoVITS: Voice reference model synthesized locally."}
          </p>
        </div>

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
