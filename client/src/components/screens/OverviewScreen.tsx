import React, { useState, useEffect } from "react";
import {
  IconPencil,
  IconArrowRight,
  IconPlus,
  IconCamera,
} from "@tabler/icons-react";
import { avatarSocket, avatarEvents } from "../../networking";
import "./OverviewScreen.css";

interface OverviewScreenProps {
  character: string;
  onStartChat: () => void;
}

interface ModelOption {
  id: string;
  name: string;
}

const PROVIDER_MODELS: Record<string, ModelOption[]> = {
  mistral: [
    { id: "ministral-8b-latest", name: "Ministral 8B (Default)" },
    { id: "mistral-small-latest", name: "Mistral Small" },
    { id: "open-mistral-7b", name: "Open Mistral 7B" },
  ],
  freeai: [
    { id: "qwen7b", name: "Qwen 2.5 7B (Fast / Free)" },
    { id: "qwen3-8b", name: "Qwen 3 8B" },
    { id: "mistral", name: "Mistral 7B" },
    { id: "deepseek-r1", name: "DeepSeek R1 Distill" },
  ],
};

export const OverviewScreen: React.FC<OverviewScreenProps> = ({
  character,
  onStartChat,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "voice">("overview");
  const [voiceEngine, setVoiceEngine] = useState<"fish" | "sovits">("fish");

  const [provider, setProvider] = useState<string>(() => {
    return (
      avatarSocket.lastConfig?.llm_provider ||
      localStorage.getItem("akari_llm_provider") ||
      "mistral"
    );
  });

  const [selectedModel, setSelectedModel] = useState<string>(() => {
    return (
      avatarSocket.lastConfig?.llm_model ||
      localStorage.getItem("akari_llm_model") ||
      "ministral-8b-latest"
    );
  });

  useEffect(() => {
    const unsubscribe = avatarEvents.subscribe("config", (event) => {
      if (event.llm_provider) {
        setProvider(event.llm_provider);
      }
      if (event.llm_model) {
        setSelectedModel(event.llm_model);
      }
    });
    return unsubscribe;
  }, []);

  const handleProviderSelect = (newProvider: string) => {
    setProvider(newProvider);
    const defaultModel =
      newProvider === "freeai" ? "qwen7b" : "ministral-8b-latest";
    setSelectedModel(defaultModel);
    localStorage.setItem("akari_llm_provider", newProvider);
    localStorage.setItem("akari_llm_model", defaultModel);
    avatarSocket.setLlmProvider(newProvider, defaultModel);
  };

  const handleModelSelect = (newModel: string) => {
    setSelectedModel(newModel);
    localStorage.setItem("akari_llm_model", newModel);
    avatarSocket.setLlmProvider(provider, newModel);
  };

  const currentModels = PROVIDER_MODELS[provider] || PROVIDER_MODELS.mistral;
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

        {/* ─── LLM Provider & Model Section (Overview Tab) ───────────── */}
        {activeTab === "overview" && (
          <div className="panel-llm-section">
            <div className="panel-llm-header">
              <span className="panel-llm-title">AI Provider</span>
              <span className="panel-llm-active-badge">
                {provider === "freeai" ? "Free.ai" : "Mistral AI"}
              </span>
            </div>

            <div className="panel-llm-toggles">
              <button
                type="button"
                className={`panel-llm-toggle-btn ${provider === "mistral" ? "active" : ""}`}
                onClick={() => handleProviderSelect("mistral")}
              >
                Mistral AI
              </button>
              <button
                type="button"
                className={`panel-llm-toggle-btn ${provider === "freeai" ? "active" : ""}`}
                onClick={() => handleProviderSelect("freeai")}
              >
                Free.ai
              </button>
            </div>

            {/* Model picker */}
            <div className="panel-llm-model-picker">
              <div className="panel-llm-model-row-header">
                <span className="panel-llm-picker-label">Model</span>
                <span className="panel-llm-model-name-badge">{selectedModel}</span>
              </div>
              <div className="panel-llm-model-chips">
                {currentModels.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    className={`panel-llm-chip ${selectedModel === m.id ? "active" : ""}`}
                    onClick={() => handleModelSelect(m.id)}
                    title={m.name}
                  >
                    {m.id}
                  </button>
                ))}
              </div>
            </div>

            <p className="panel-llm-caption">
              {provider === "freeai"
                ? `Free.ai API: Streamed via ${selectedModel} (30K daily free tokens).`
                : `Mistral AI: Official API streaming via ${selectedModel}.`}
            </p>
          </div>
        )}

        {/* Voice engine configuration (Voice Tab) */}
        {activeTab === "voice" && (
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
