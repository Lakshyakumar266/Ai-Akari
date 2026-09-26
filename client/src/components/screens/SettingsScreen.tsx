import React, { useEffect, useState } from "react";
import {
  IconCpu,
  IconSparkles,
  IconCheck,
  IconLink,
  IconCopy,
  IconChecklist,
  IconTools,
  IconClock,
  IconCalendar,
  IconDeviceDesktopAnalytics,
  IconAlertCircle,
  IconCalculator,
  IconArrowsExchange,
  IconWorld,
  IconCalendarTime,
} from "@tabler/icons-react";
import { avatarEvents } from "../../networking";
import "./SettingsScreen.css";

interface SettingsScreenProps {
  currentProvider: string;
  currentModel: string;
  currentToolsEnabled?: boolean;
  onUpdateLlm: (provider: string, model?: string) => void;
  onUpdateTools?: (enabled: boolean) => void;
}

interface ModelDetail {
  id: string;
  name: string;
  badge?: string;
  context: string;
  toolCallingSupported: boolean;
}

interface ProviderDetail {
  id: "mistral" | "freeai" | "openrouter";
  name: string;
  badge: string;
  toolCallingSupported: boolean;
  models: ModelDetail[];
}

const PROVIDERS: ProviderDetail[] = [
  {
    id: "mistral",
    name: "Mistral AI",
    badge: "Official API",
    toolCallingSupported: true,
    models: [
      {
        id: "ministral-8b-latest",
        name: "Ministral 8B",
        badge: "Recommended",
        context: "128k context",
        toolCallingSupported: true,
      },
      {
        id: "mistral-small-latest",
        name: "Mistral Small",
        badge: "Reasoning",
        context: "32k context",
        toolCallingSupported: true,
      },
      {
        id: "open-mistral-7b",
        name: "Open Mistral 7B",
        badge: "Baseline",
        context: "32k context",
        toolCallingSupported: true,
      },
    ],
  },
  {
    id: "freeai",
    name: "Free.ai",
    badge: "Free Gateway",
    toolCallingSupported: true,
    models: [
      {
        id: "qwen7b",
        name: "Qwen 2.5 7B",
        badge: "Recommended",
        context: "32k context",
        toolCallingSupported: true,
      },
      {
        id: "qwen3-8b",
        name: "Qwen 3 8B",
        badge: "Next-Gen",
        context: "32k context",
        toolCallingSupported: true,
      },
      {
        id: "mistral",
        name: "Mistral 7B",
        badge: "Fast Inference",
        context: "32k context",
        toolCallingSupported: false,
      },
      {
        id: "deepseek-r1",
        name: "DeepSeek R1 Distill",
        badge: "Chain of Thought",
        context: "64k context",
        toolCallingSupported: false,
      },
    ],
  },
  {
    id: "openrouter",
    name: "OpenRouter (Free)",
    badge: "Free Tier",
    toolCallingSupported: true,
    models: [
      {
        id: "openrouter/free",
        name: "Free Models Router",
        badge: "Auto (Recommended)",
        context: "200k context",
        toolCallingSupported: true,
      },
      {
        id: "inclusionai/ling-3.0-flash-sante:free",
        name: "Ling 3.0 Flash",
        badge: "Fast",
        context: "262k context",
        toolCallingSupported: true,
      },
      {
        id: "liquid/lfm-2.5-2.6b:free",
        name: "Liquid LFM 2.5",
        badge: "Lightweight",
        context: "65k context",
        toolCallingSupported: true,
      },
      {
        id: "stealth/space-bunny-alpha",
        name: "Space Bunny Alpha",
        badge: "1M Context",
        context: "1M context",
        toolCallingSupported: true,
      },
      {
        id: "poolside/laguna-s-2.1:free",
        name: "Laguna S 2.1",
        badge: "Reasoning",
        context: "262k context",
        toolCallingSupported: true,
      },
      {
        id: "qwen/qwen3.8-27b:free",
        name: "Qwen 3.8 27B",
        badge: "Multilingual",
        context: "262k context",
        toolCallingSupported: true,
      },
    ],
  },
];

export const SettingsScreen: React.FC<SettingsScreenProps> = ({
  currentProvider,
  currentModel,
  currentToolsEnabled = false,
  onUpdateLlm,
  onUpdateTools,
}) => {
  const [provider, setProvider] = useState<string>(currentProvider || "mistral");
  const [model, setModel] = useState<string>(currentModel || "ministral-8b-latest");
  const [toolsEnabled, setToolsEnabled] = useState<boolean>(currentToolsEnabled);
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

  useEffect(() => {
    if (currentToolsEnabled !== undefined && currentToolsEnabled !== toolsEnabled) {
      setToolsEnabled(currentToolsEnabled);
    }
  }, [currentToolsEnabled]);

  // Listen to live config broadcast from backend
  useEffect(() => {
    const unsubscribe = avatarEvents.subscribe("config", (event) => {
      if (event.llm_provider) {
        setProvider(event.llm_provider);
      }
      if (event.llm_model) {
        setModel(event.llm_model);
      }
      if (typeof event.tool_calling_enabled === "boolean") {
        setToolsEnabled(event.tool_calling_enabled);
      }
    });
    return unsubscribe;
  }, []);

  const activeProviderDetail =
    PROVIDERS.find((p) => p.id === provider) || PROVIDERS[0];

  const activeModelDetail =
    activeProviderDetail.models.find((m) => m.id === model) ||
    activeProviderDetail.models[0];

  const isCurrentModelToolSupported = activeModelDetail?.toolCallingSupported ?? false;

  const handleSelectProvider = (newProviderId: "mistral" | "freeai" | "openrouter") => {
    if (newProviderId === provider) return;
    const targetProviderObj = PROVIDERS.find((p) => p.id === newProviderId)!;
    const defaultModelObj = targetProviderObj.models[0];
    const defaultModel = defaultModelObj.id;

    setProvider(newProviderId);
    setModel(defaultModel);
    onUpdateLlm(newProviderId, defaultModel);

    // If new model does not support tool calling, disable tool calling immediately
    if (!defaultModelObj.toolCallingSupported && toolsEnabled) {
      setToolsEnabled(false);
      onUpdateTools?.(false);
    }
  };

  const handleSelectModel = (newModelId: string) => {
    const selectedModelObj = activeProviderDetail.models.find((m) => m.id === newModelId);
    setModel(newModelId);
    onUpdateLlm(provider, newModelId);

    // If newly chosen model does not support tool calling, automatically disable
    if (selectedModelObj && !selectedModelObj.toolCallingSupported && toolsEnabled) {
      setToolsEnabled(false);
      onUpdateTools?.(false);
    }
  };

  const handleToggleTools = () => {
    if (!isCurrentModelToolSupported) return;
    const nextState = !toolsEnabled;
    setToolsEnabled(nextState);
    onUpdateTools?.(nextState);
  };

  const currentUrlPreview =
    typeof window !== "undefined"
      ? `${window.location.origin}/?screen=settings&character=akari&provider=${provider}&model=${model}&tools=${
          toolsEnabled && isCurrentModelToolSupported ? "true" : "false"
        }`
      : `/?screen=settings&character=akari&provider=${provider}&model=${model}&tools=${
          toolsEnabled && isCurrentModelToolSupported ? "true" : "false"
        }`;

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
            Configure AI inference provider, language reasoning model, tool capabilities, and URL synchronization.
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
                      {m.toolCallingSupported ? (
                        <span className="row-tool-badge supported" title="Supports Tool Calling">
                          Tools Ready
                        </span>
                      ) : (
                        <span className="row-tool-badge unsupported" title="Tool Calling Not Supported">
                          No Tools
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

        {/* ─── Dedicated Tool Calling Configuration Section ───────────── */}
        <section className="settings-section" aria-labelledby="tools-heading">
          <div className="section-label-row">
            <IconTools size={16} className="section-icon" />
            <span id="tools-heading" className="section-label">
              Tool Calling Capability
            </span>
            <span
              className={`capability-status-tag ${
                isCurrentModelToolSupported ? "supported" : "unsupported"
              }`}
            >
              {isCurrentModelToolSupported ? "Model Supported" : "Model Unsupported"}
            </span>
          </div>

          <div className={`tools-master-card ${!isCurrentModelToolSupported ? "disabled-card" : ""}`}>
            <div className="tools-card-header">
              <div className="tools-card-text">
                <div className="tools-card-title">
                  <span>Enable Tool Calling</span>
                  {isCurrentModelToolSupported ? (
                    <span className="tool-card-badge active">Supported by {activeModelDetail.name}</span>
                  ) : (
                    <span className="tool-card-badge inactive">Incompatible with {activeModelDetail.name}</span>
                  )}
                </div>
                <p className="tools-card-desc">
                  {isCurrentModelToolSupported
                    ? "Allows Akari to invoke external tools (such as live time, date, and system status) to provide accurate answers rather than hallucinating."
                    : "The selected model does not support tool calling. Choose a compatible model (e.g. Ministral 8B or Qwen 2.5 7B) to enable this feature."}
                </p>
              </div>

              <button
                type="button"
                className={`tool-toggle-btn ${
                  toolsEnabled && isCurrentModelToolSupported ? "active" : ""
                } ${!isCurrentModelToolSupported ? "disabled" : ""}`}
                onClick={handleToggleTools}
                disabled={!isCurrentModelToolSupported}
                aria-pressed={toolsEnabled && isCurrentModelToolSupported}
                title={
                  !isCurrentModelToolSupported
                    ? "The selected model does not support tool calling"
                    : toolsEnabled
                    ? "Click to disable tool calling"
                    : "Click to enable tool calling"
                }
              >
                <span className="tool-toggle-track">
                  <span className="tool-toggle-thumb" />
                </span>
                <span className="tool-toggle-label">
                  {!isCurrentModelToolSupported ? "Disabled" : toolsEnabled ? "ON" : "OFF"}
                </span>
              </button>
            </div>

            {/* Available Tools Grid */}
            <div className="available-tools-header">
              <span className="available-tools-title">Available Tools</span>
              <span
                className="available-tools-limit"
                title="Safety limit: Maximum number of sequential tool execution iterations permitted within a single user message turn to prevent runaway loops."
              >
                Max: 5 rounds / turn
              </span>
            </div>

            <div className="available-tools-grid">
              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconTools size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Tool Discovery</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Allows model to dynamically list and inspect all capabilities
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconClock size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Current Time</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Retrieves live time in 12h/24h format for any location
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconWorld size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Timezone Details</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Resolves timezone IANA code, UTC offset, and DST
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconArrowsExchange size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Time Converter</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Converts specific times between any two cities
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconArrowsExchange size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Time Difference</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Computes hours offset and compares time zones
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconCalendar size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Current Date</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Retrieves current day, month, date, and year
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconCalendarTime size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Day of Week</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Finds the weekday and relative days for any date
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconCalculator size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">Calculator</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Safe AST math, percentages, powers, and expressions
                  </span>
                </div>
              </div>

              <div
                className={`tool-item-card ${
                  isCurrentModelToolSupported && toolsEnabled ? "active" : "dormant"
                }`}
              >
                <div className="tool-item-icon-box">
                  <IconDeviceDesktopAnalytics size={16} />
                </div>
                <div className="tool-item-info">
                  <div className="tool-item-name-row">
                    <span className="tool-item-name">System Status</span>
                    <span className="tool-item-status">
                      {isCurrentModelToolSupported && toolsEnabled ? "Ready" : "Inactive"}
                    </span>
                  </div>
                  <span className="tool-item-desc">
                    Checks system health, OS runtime, and model status
                  </span>
                </div>
              </div>
            </div>

            {!isCurrentModelToolSupported && (
              <div className="unsupported-model-warning">
                <IconAlertCircle size={15} />
                <span>
                  Tool Calling is disabled because <strong>{activeModelDetail.name}</strong> lacks native function calling capabilities.
                </span>
              </div>
            )}
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
                ?screen=settings&provider={provider}&model={model}&tools={
                  toolsEnabled && isCurrentModelToolSupported ? "true" : "false"
                }
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
