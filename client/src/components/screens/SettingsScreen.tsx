import React, { useEffect, useState } from "react";
import {
  IconCpu,
  IconSparkles,
  IconCheck,
  IconLink,
  IconCopy,
  IconChecklist,
} from "@tabler/icons-react";
import { avatarEvents } from "../../networking";
import "./SettingsScreen.css";

interface SettingsScreenProps {
  currentProvider: string;
  currentModel: string;
  onUpdateLlm: (provider: string, model?: string) => void;
}

interface ModelDetail {
  id: string;
  name: string;
  badge?: string;
  context: string;
}

interface ProviderDetail {
  id: "mistral" | "freeai";
  name: string;
  badge: string;
  models: ModelDetail[];
}

const PROVIDERS: ProviderDetail[] = [
  {
    id: "mistral",
    name: "Mistral AI",
    badge: "Official API",
    models: [
      {
        id: "ministral-8b-latest",
        name: "Ministral 8B",
        badge: "Recommended",
        context: "128k context",
      },
      {
        id: "mistral-small-latest",
        name: "Mistral Small",
        badge: "Reasoning",
        context: "32k context",
      },
      {
        id: "open-mistral-7b",
        name: "Open Mistral 7B",
        badge: "Baseline",
        context: "32k context",
      },
    ],
  },
  {
    id: "freeai",
    name: "Free.ai",
    badge: "Free Gateway",
    models: [
      {
        id: "qwen7b",
        name: "Qwen 2.5 7B",
        badge: "Recommended",
        context: "32k context",
      },
      {
        id: "qwen3-8b",
        name: "Qwen 3 8B",
        badge: "Next-Gen",
        context: "32k context",
      },
      {
        id: "mistral",
        name: "Mistral 7B",
        badge: "Fast Inference",
        context: "32k context",
      },
      {
        id: "deepseek-r1",
        name: "DeepSeek R1 Distill",
        badge: "Chain of Thought",
        context: "64k context",
      },
    ],
  },
];

export const SettingsScreen: React.FC<SettingsScreenProps> = ({
  currentProvider,
  currentModel,
  onUpdateLlm,
}) => {
  const [provider, setProvider] = useState<string>(currentProvider || "mistral");
  const [model, setModel] = useState<string>(currentModel || "ministral-8b-latest");
  const [isCopied, setIsCopied] = useState(false);

  // Sync state if props change from outside (e.g. browser back/forward)
  useEffect(() => {
    if (currentProvider && currentProvider !== provider) {
      setProvider(currentProvider);
    }
  }, [currentProvider]);

  useEffect(() => {
    if (currentModel && currentModel !== model) {
      setModel(currentModel);
    }
  }, [currentModel]);

  // Listen to live config broadcast from backend
  useEffect(() => {
    const unsubscribe = avatarEvents.subscribe("config", (event) => {
      if (event.llm_provider) {
        setProvider(event.llm_provider);
      }
      if (event.llm_model) {
        setModel(event.llm_model);
      }
    });
    return unsubscribe;
  }, []);

  const activeProviderDetail =
    PROVIDERS.find((p) => p.id === provider) || PROVIDERS[0];

  const handleSelectProvider = (newProviderId: "mistral" | "freeai") => {
    if (newProviderId === provider) return;
    const targetProviderObj = PROVIDERS.find((p) => p.id === newProviderId)!;
    const defaultModel = targetProviderObj.models[0].id;
    setProvider(newProviderId);
    setModel(defaultModel);
    onUpdateLlm(newProviderId, defaultModel);
  };

  const handleSelectModel = (newModelId: string) => {
    setModel(newModelId);
    onUpdateLlm(provider, newModelId);
  };

  const currentUrlPreview =
    typeof window !== "undefined"
      ? `${window.location.origin}/?screen=settings&character=akari&provider=${provider}&model=${model}`
      : `/?screen=settings&character=akari&provider=${provider}&model=${model}`;

  const copyUrl = () => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(currentUrlPreview);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div className="settings-screen-root" aria-label="Application Settings Screen">
      <div className="settings-container">
        {/* ─── Compact Header ────────────────────────────────────────── */}
        <header className="settings-header">
          <div className="settings-category-tag">PREFERENCES</div>
          <h1 className="settings-title">Settings</h1>
          <p className="settings-subtitle">
            Configure AI inference provider, language reasoning model, and URL synchronization.
          </p>
        </header>

        {/* ─── Provider Segmented Selector ───────────────────────────── */}
        <section className="settings-section" aria-labelledby="provider-heading">
          <div className="section-label-row">
            <IconCpu size={16} className="section-icon" />
            <span id="provider-heading" className="section-label">
              Inference Provider
            </span>
          </div>

          <div className="provider-segment-group">
            {PROVIDERS.map((p) => {
              const isSelected = provider === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  className={`provider-segment-btn ${isSelected ? "active" : ""}`}
                  onClick={() => handleSelectProvider(p.id)}
                  aria-pressed={isSelected}
                >
                  <span className="segment-btn-dot" />
                  <span className="segment-btn-name">{p.name}</span>
                  <span className="segment-btn-badge">{p.badge}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* ─── Compact Model List ────────────────────────────────────── */}
        <section className="settings-section" aria-labelledby="model-heading">
          <div className="section-label-row">
            <IconSparkles size={16} className="section-icon sparkles" />
            <span id="model-heading" className="section-label">
              Model Selection
            </span>
            <span className="section-count-badge">
              {activeProviderDetail.models.length} available
            </span>
          </div>

          <div className="compact-model-list" role="radiogroup" aria-labelledby="model-heading">
            {activeProviderDetail.models.map((m) => {
              const isSelected = model === m.id;
              return (
                <div
                  key={m.id}
                  className={`compact-model-row ${isSelected ? "selected" : ""}`}
                  onClick={() => handleSelectModel(m.id)}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && handleSelectModel(m.id)}
                >
                  <div className={`row-radio-indicator ${isSelected ? "active" : ""}`}>
                    {isSelected && <IconCheck size={12} stroke={3} />}
                  </div>

                  <div className="row-info-col">
                    <div className="row-title-line">
                      <span className="row-model-name">{m.name}</span>
                      {m.badge && (
                        <span
                          className={`row-badge ${
                            m.badge.includes("Recommended") ? "recommended" : ""
                          }`}
                        >
                          {m.badge}
                        </span>
                      )}
                    </div>
                    <code className="row-model-id">{m.id}</code>
                  </div>

                  <span className="row-context-tag">{m.context}</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* ─── Slim URL Sync Bar ─────────────────────────────────────── */}
        <section className="settings-section" aria-labelledby="sync-heading">
          <div className="section-label-row">
            <IconLink size={15} className="section-icon" />
            <span id="sync-heading" className="section-label">
              URL Synchronization
            </span>
          </div>

          <div className="slim-sync-bar">
            <div className="sync-bar-left">
              <span className="sync-live-dot" />
              <code className="sync-url-text">
                ?screen=settings&provider={provider}&model={model}
              </code>
            </div>

            <button
              type="button"
              className="sync-copy-btn"
              onClick={copyUrl}
              title="Copy URL parameter link"
            >
              {isCopied ? <IconChecklist size={14} /> : <IconCopy size={14} />}
              <span>{isCopied ? "Copied" : "Copy"}</span>
            </button>
          </div>
        </section>

        {/* Bottom margin spacer for scrolling clearance */}
        <div className="settings-bottom-spacer" />
      </div>
    </div>
  );
};
