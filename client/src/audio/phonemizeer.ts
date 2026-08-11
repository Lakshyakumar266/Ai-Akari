import { phonemize, toARPABET, toIPA } from "phonemize/all";

export type Viseme = "aa" | "ih" | "ou" | "ee" | "oh" | "sil";

const ARPABET_MAP: Record<string, Viseme> = {
  // Open vowels
  AA: "aa",
  AO: "aa",
  AH: "aa",
  ER: "aa",
  AX: "aa",
  AXR: "aa",

  // Front high vowels
  IH: "ih",
  IY: "ih",
  Y: "ih",

  // Rounded high vowels
  UW: "ou",
  UH: "ou",
  W: "ou",

  // Front mid/low vowels
  EH: "ee",
  EY: "ee",
  AE: "ee",
  AY: "ee",

  // Rounded mid vowels
  OW: "oh",
  OY: "oh",
  AW: "oh",

  // Bilabial consonants (closed lips)
  P: "sil",
  B: "sil",
  M: "sil",
  EM: "sil",

  // Neutral lingual consonants
  F: "ih",
  V: "ih",
  TH: "ih",
  DH: "ih",
  S: "ih",
  Z: "ih",
  SH: "ih",
  ZH: "ih",
  CH: "ih",
  JH: "ih",
  T: "ih",
  D: "ih",
  K: "ih",
  G: "ih",
  N: "ih",
  NG: "ih",
  L: "ih",
  R: "ih",
  HH: "ih",
  DX: "ih",
};

export function phonemeToViseme(phoneme: string): Viseme {
  const p = phoneme.toUpperCase().replace(/[012]/g, "").trim();
  if (!p) return "sil";

  const mapped = ARPABET_MAP[p];
  if (mapped) return mapped;

  // IPA fallback check (lowercase)
  const lower = phoneme.toLowerCase().replace(/[ˈˌ]/g, "").trim();
  if (!lower) return "sil";

  if (/[aɑɒʌä]/.test(lower)) return "aa";
  if (/[iɪjy]/.test(lower)) return "ih";
  if (/[uʊw]/.test(lower)) return "ou";
  if (/[eɛæ]/.test(lower)) return "ee";
  if (/[oɔ]/.test(lower)) return "oh";
  if (/[pbm]/.test(lower)) return "sil";

  return "sil";
}

export function textToPhonemes(text: string): string[] {
  if (!text || !text.trim()) return [];
  const arpabetStr = toARPABET(text);
  return arpabetStr
    .trim()
    .split(/\s+/)
    .filter((token) => token.length > 0);
}

export function textToVisemes(text: string): Viseme[] {
  const phonemes = textToPhonemes(text);
  return phonemes.map(phonemeToViseme);
}

export { phonemize, toARPABET, toIPA };

/**
 * Phonemizer Module
 * Maps text strings into ARPABET phonetic tokens and categorizes them into standard 3D VRM mouth visemes.
 */