/**
 * SubtitleOverlay
 *
 * Anime-styled karaoke subtitle overlay that displays Akari's speech
 * word-by-word, highlighting each word as it is spoken.
 *
 * Sync strategy: Audio chunk bytes → elapsed audio seconds → word index.
 * Fish Audio PCM is 44100 Hz Int16 mono = 88200 bytes/second.
 * We estimate ~3 words/second for typical TTS speech and advance
 * the highlight cursor proportionally to audio received.
 *
 * - Shows 2 lines at a time
 * - Words highlight one-by-one synced to audio chunk progress
 * - Auto-scrolls to the next pair of lines
 * - Fades out after speech ends
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { avatarEvents } from "../networking/EventBus";
import { subtitleSync } from "../audio/SubtitleSync";
import type { SubtitleEvent } from "../networking/types";

// ─── Constants ────────────────────────────────────────────────────────────────

/** How many words per visual line (approximate). */
const WORDS_PER_LINE = 7;

/** Estimated words-per-second for TTS speech. */
const WORDS_PER_SECOND = 3.2;

/** Delay (ms) after speech_end before fading out. */
const FADEOUT_DELAY_MS = 1200;

/** Duration of the fade-out animation (ms). */
const FADEOUT_DURATION_MS = 600;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function splitWords(text: string): string[] {
  return text.split(/\s+/).filter((w) => w.length > 0);
}

function groupIntoLines(words: string[]): string[][] {
  const lines: string[][] = [];
  for (let i = 0; i < words.length; i += WORDS_PER_LINE) {
    lines.push(words.slice(i, i + WORDS_PER_LINE));
  }
  return lines;
}

/**
 * Compute the global word index for a word at position `wordIdx`
 * within line `lineIdx`, given the actual line lengths.
 */
function globalWordIndex(lines: string[][], lineIdx: number, wordIdx: number): number {
  let idx = 0;
  for (let i = 0; i < lineIdx; i++) {
    idx += lines[i]?.length ?? 0;
  }
  return idx + wordIdx;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function SubtitleOverlay() {
  const [words, setWords] = useState<string[]>([]);
  const [lines, setLines] = useState<string[][]>([]);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const [visibleLineStart, setVisibleLineStart] = useState(0);
  const [opacity, setOpacity] = useState(0);

  const isSpeakingRef = useRef(false);
  const totalWordsRef = useRef(0);
  const linesRef = useRef<string[][]>([]);
  const rafIdRef = useRef<number | null>(null);
  const fadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─── Audio-chunk-driven highlight loop ────────────────────────────────

  const tick = useCallback(() => {
    if (!isSpeakingRef.current) return;

    const elapsed = subtitleSync.elapsedSeconds;
    const totalWords = totalWordsRef.current;

    if (totalWords <= 0) {
      rafIdRef.current = requestAnimationFrame(tick);
      return;
    }

    // Compute which word we should be on based on elapsed audio time
    const wordIdx = Math.min(
      Math.floor(elapsed * WORDS_PER_SECOND),
      totalWords - 1
    );

    setHighlightIndex(wordIdx);

    // Figure out which line pair should be visible
    const currentLineIdx = Math.floor(wordIdx / WORDS_PER_LINE);
    const pairStart = Math.floor(currentLineIdx / 2) * 2;
    setVisibleLineStart(pairStart);

    rafIdRef.current = requestAnimationFrame(tick);
  }, []);

  // ─── Event subscriptions ──────────────────────────────────────────────

  useEffect(() => {
    const unsubSubtitle = avatarEvents.subscribe(
      "subtitle",
      (event: SubtitleEvent) => {
        const w = splitWords(event.text);
        const l = groupIntoLines(w);

        totalWordsRef.current = w.length;
        linesRef.current = l;

        setWords(w);
        setLines(l);
        setHighlightIndex(-1);
        setVisibleLineStart(0);
        setOpacity(1);

        // Clear any pending fade-out
        if (fadeTimerRef.current) {
          clearTimeout(fadeTimerRef.current);
          fadeTimerRef.current = null;
        }
      }
    );

    const unsubStart = avatarEvents.subscribe("speech_start", () => {
      isSpeakingRef.current = true;
      subtitleSync.reset();

      // Start the RAF loop
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
      }
      rafIdRef.current = requestAnimationFrame(tick);
    });

    const unsubEnd = avatarEvents.subscribe("speech_end", () => {
      isSpeakingRef.current = false;

      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }

      // Highlight all remaining words
      setHighlightIndex(totalWordsRef.current - 1);

      // Scroll to show the last line pair
      const lastLineIdx = Math.max(0, linesRef.current.length - 1);
      const lastPairStart = Math.floor(lastLineIdx / 2) * 2;
      setVisibleLineStart(lastPairStart);

      // Fade out after delay
      fadeTimerRef.current = setTimeout(() => {
        setOpacity(0);
        setTimeout(() => {
          setWords([]);
          setLines([]);
          setHighlightIndex(-1);
          setVisibleLineStart(0);
        }, FADEOUT_DURATION_MS);
      }, FADEOUT_DELAY_MS);
    });

    return () => {
      unsubSubtitle();
      unsubStart();
      unsubEnd();
      if (rafIdRef.current !== null) cancelAnimationFrame(rafIdRef.current);
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
    };
  }, [tick]);

  // ─── Render ───────────────────────────────────────────────────────────

  if (words.length === 0) return null;

  const visibleLines = lines.slice(visibleLineStart, visibleLineStart + 2);

  return (
    <div style={styles.container} className="subtitle-overlay">
      <div
        style={{
          ...styles.textContainer,
          opacity,
          transition: `opacity ${FADEOUT_DURATION_MS}ms ease`,
        }}
      >
        {visibleLines.map((line, lineIdx) => {
          const actualLineIdx = visibleLineStart + lineIdx;
          return (
            <div key={`line-${actualLineIdx}`} style={styles.line}>
              {line.map((word, wordIdx) => {
                const gIdx = globalWordIndex(lines, actualLineIdx, wordIdx);
                const isHighlighted = gIdx <= highlightIndex;
                const isCurrent = gIdx === highlightIndex;

                return (
                  <span
                    key={`w-${gIdx}`}
                    style={{
                      ...styles.word,
                      ...(isHighlighted ? styles.wordHighlighted : styles.wordDim),
                      ...(isCurrent ? styles.wordCurrent : {}),
                    }}
                  >
                    {word}{" "}
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>

      <style>{cssText}</style>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const cssText = `
@import url('https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;700;900&display=swap');

@keyframes subtitle-glow-pulse {
  0%, 100% { text-shadow:
    -2px -2px 0 #1a0a1f,
     2px -2px 0 #1a0a1f,
    -2px  2px 0 #1a0a1f,
     2px  2px 0 #1a0a1f,
    0 0 8px rgba(255, 100, 180, 0.5);
  }
  50% { text-shadow:
    -2px -2px 0 #1a0a1f,
     2px -2px 0 #1a0a1f,
    -2px  2px 0 #1a0a1f,
     2px  2px 0 #1a0a1f,
    0 0 16px rgba(255, 100, 180, 0.8),
    0 0 32px rgba(255, 60, 150, 0.4);
  }
}

.subtitle-overlay * {
  -webkit-text-stroke: 1.5px #1a0a1f;
  paint-order: stroke fill;
}
`;

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: "fixed",
    bottom: "6%",
    left: 0,
    right: 0,
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    pointerEvents: "none",
    zIndex: 100,
  },

  textContainer: {
    maxWidth: "85vw",
    textAlign: "center",
    padding: "12px 24px",
    borderRadius: "12px",
    background: "linear-gradient(135deg, rgba(15, 5, 20, 0.55), rgba(30, 10, 40, 0.45))",
    backdropFilter: "blur(8px)",
    border: "1px solid rgba(255, 100, 180, 0.15)",
  },

  line: {
    fontFamily: "'Zen Kaku Gothic New', 'Hiragino Kaku Gothic Pro', sans-serif",
    fontSize: "clamp(1.1rem, 2.8vw, 1.6rem)",
    fontWeight: 900,
    lineHeight: 1.7,
    letterSpacing: "0.03em",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },

  word: {
    display: "inline",
    transition: "color 0.12s ease, text-shadow 0.12s ease",
  },

  wordDim: {
    color: "rgba(200, 190, 210, 0.45)",
    textShadow: `
      -2px -2px 0 #1a0a1f,
       2px -2px 0 #1a0a1f,
      -2px  2px 0 #1a0a1f,
       2px  2px 0 #1a0a1f
    `,
  },

  wordHighlighted: {
    color: "#fff",
    textShadow: `
      -2px -2px 0 #1a0a1f,
       2px -2px 0 #1a0a1f,
      -2px  2px 0 #1a0a1f,
       2px  2px 0 #1a0a1f,
      0 0 8px rgba(255, 100, 180, 0.5)
    `,
  },

  wordCurrent: {
    color: "#ff6cb4",
    animation: "subtitle-glow-pulse 0.8s ease-in-out infinite",
    textShadow: `
      -2px -2px 0 #1a0a1f,
       2px -2px 0 #1a0a1f,
      -2px  2px 0 #1a0a1f,
       2px  2px 0 #1a0a1f,
      0 0 12px rgba(255, 100, 180, 0.7),
      0 0 24px rgba(255, 60, 150, 0.4)
    `,
  },
};
