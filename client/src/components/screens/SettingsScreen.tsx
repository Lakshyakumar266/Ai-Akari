import React, { useEffect, useState } from "react";
import {
  IconCpu,
  IconSparkles,
  IconCheck,
  IconLink,
  IconShieldCheck,
  IconBolt,
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
  description: string;
  contextWindow: string;
}

interface ProviderDetail {
  id: "mistral" | "freeai";
  name: string;
  badge: string;
  endpoint: string;
  description: string;
  models: ModelDetail[];
}

const PROVIDERS: ProviderDetail[] = [
  {
    id: "mistral",
    name: "Mistral AI",
    badge: "Official API",
    endpoint: "https://api.mistral.ai/v1",
    description:
      "Enterprise-grade inference hosted directly by Mistral. Excellent reasoning, natural roleplay flow, and low latency streaming.",
    models: [
      {
        id: "ministral-8b-latest",
        name: "Ministral 8B",
        badge: "Recommended",
        description: "Optimal balance of edge latency and natural companion dialogue.",
        contextWindow: "128k context",
      },
      {
        id: "mistral-small-latest",
        name: "Mistral Small",
        badge: "Deep Reasoning",
        description: "Higher reasoning capacity with enhanced multilingual comprehension.",
        contextWindow: "32k context",
      },
      {
        id: "open-mistral-7b",
        name: "Open Mistral 7B",
        badge: "Standard",
        description: "Classic open-weights conversational baseline.",
        contextWindow: "32k context",
      },
    ],
  },
  {
    id: "freeai",
    name: "Free.ai",
    badge: "Free Gateway",
    endpoint: "https://api.free.ai/v1",
    description:
      "Multi-model AI gateway offering 30,000 free daily tokens across leading open source LLMs like Qwen, Mistral, and DeepSeek.",
    models: [
      {
        id: "qwen7b",
        name: "Qwen 2.5 7B",
        badge: "Recommended",
        description: "High speed, creative conversational nuances, and outstanding multilingual support.",
        contextWindow: "32k context",
      },
      {
        id: "qwen3-8b",
        name: "Qwen 3 8B",
        badge: "Next-Gen",
        description: "Latest generation architecture with enhanced instruction following.",
        contextWindow: "32k context",
      },
      {
        id: "mistral",
        name: "Mistral 7B",
        badge: "Fast Inference",
        description: "Fast generalist language model hosted on Free.ai infrastructure.",
        contextWindow: "32k context",
      },
      {
        id: "deepseek-r1",
        name: "DeepSeek R1 Distill",
        badge: "Chain of Thought",
        description: "Distilled reasoning model adept at complex logic and planning.",
        contextWindow: "64k context",
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

  // Sync state if props change from outside (e.g. popstate navigation)
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

  const currentUrlPreview = typeof window !== "undefined"
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
        {/* ─── Header Section ────────────────────────────────────────────── */}
        <header className="settings-header">
          <div className="settings-category-tag">SYSTEM / PREFERENCES</div>
          <h1 className="settings-title">Settings</h1>
          <p className="settings-subtitle">
            Configure the AI language reasoning engine, active provider, and URL synchronization parameters.
          </p>
        </header>

        {/* ─── 1. Provider Selection Cards ───────────────────────────────── */}
        <section className="settings-section" aria-labelledby="provider-heading">
          <div className="section-title-row">
            <IconCpu size={20} className="section-icon" />
            <h2 id="provider-heading" className="section-title">
              Inference Provider
            </h2>
            <span className="section-badge">Active: {activeProviderDetail.name}</span>
          </div>

          <div className="provider-grid">
            {PROVIDERS.map((p) => {
              const isSelected = provider === p.id;
              return (
                <div
                  key={p.id}
                  className={`provider-card ${isSelected ? "selected" : ""}`}
                  onClick={() => handleSelectProvider(p.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && handleSelectProvider(p.id)}
                  aria-pressed={isSelected}
                >
                  <div className="card-top-row">
                    <div className="provider-info-group">
                      <h3 className="provider-card-name">{p.name}</h3>
                      <span className="provider-tag">{p.badge}</span>
                    </div>
                    <div className={`radio-dot-indicator ${isSelected ? "active" : ""}`}>
                      {isSelected && <IconCheck size={14} stroke={3} />}
                    </div>
                  </div>

                  <p className="provider-card-desc">{p.description}</p>

                  <div className="card-footer-meta">
                    <span className="endpoint-code">{p.endpoint}</span>
                    {isSelected && (
                      <span className="status-pill active">
                        <IconBolt size={12} /> Connected
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ─── 2. Model Selection Grid ───────────────────────────────────── */}
        <section className="settings-section" aria-labelledby="model-heading">
          <div className="section-title-row">
            <IconSparkles size={20} className="section-icon sparkles" />
            <h2 id="model-heading" className="section-title">
              Model Selection
            </h2>
            <span className="section-badge">
              {activeProviderDetail.name} Models ({activeProviderDetail.models.length})
            </span>
          </div>

          <div className="model-grid">
            {activeProviderDetail.models.map((m) => {
              const isSelected = model === m.id;
              return (
                <div
                  key={m.id}
                  className={`model-card ${isSelected ? "selected" : ""}`}
                  onClick={() => handleSelectModel(m.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && handleSelectModel(m.id)}
                  aria-pressed={isSelected}
                >
                  <div className="card-top-row">
                    <div className="model-title-group">
                      <span className="model-display-name">{m.name}</span>
                      <code className="model-raw-id">{m.id}</code>
                    </div>
                    {m.badge && (
                      <span className={`model-badge ${m.badge === "Recommended" ? "recommended" : ""}`}>
                        {m.badge}
                      </span>
                    )}
                  </div>

                  <p className="model-desc">{m.description}</p>

                  <div className="model-card-bottom">
                    <span className="context-tag">{m.contextWindow}</span>
                    <div className={`model-radio ${isSelected ? "selected" : ""}`}>
                      {isSelected ? "Active Model" : "Select"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ─── 3. URL & Live Status Card ─────────────────────────────────── */}
        <section className="settings-section" aria-labelledby="sync-heading">
          <div className="section-title-row">
            <IconLink size={18} className="section-icon" />
            <h2 id="sync-heading" className="section-title">
              URL Synchronization & State
            </h2>
          </div>

          <div className="sync-preview-card">
            <div className="sync-card-header">
              <div className="sync-status-indicator">
                <IconShieldCheck size={16} className="text-emerald" />
                <span>Synchronized with Python Backend & URL Parameters</span>
              </div>
              <button
                type="button"
                className="copy-url-btn"
                onClick={copyUrl}
                title="Copy current URL"
              >
                {isCopied ? "Copied!" : "Copy Link"}
              </button>
            </div>

            <div className="url-preview-box">
              <code>{currentUrlPreview}</code>
            </div>

            <div className="sync-param-chips">
              <div className="param-chip">
                <span className="chip-key">provider:</span>
                <span className="chip-val">{provider}</span>
              </div>
              <div className="param-chip">
                <span className="chip-key">model:</span>
                <span className="chip-val">{model}</span>
              </div>
              <div className="param-chip">
                <span className="chip-key">backend:</span>
                <span className="chip-val">ws://127.0.0.1:8765</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
