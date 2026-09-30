from __future__ import annotations

import asyncio
from typing import Any
from mistralai.client.models import UserMessage, AssistantMessage


def _extract_role_and_text(msg: Any) -> tuple[str, str]:
    """Extracts role and plain text content from various message formats."""
    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, list):
            texts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            return "user", " ".join(texts).strip()
        return "user", str(content or "").strip()

    if isinstance(msg, AssistantMessage):
        return "assistant", str(msg.content or "").strip()

    if isinstance(msg, dict):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            texts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            return role, " ".join(texts).strip()
        return role, str(content or "").strip()

    # Fallback duck-typing for custom objects
    role = getattr(msg, "role", "user")
    content = getattr(msg, "content", str(msg))
    return role, str(content or "").strip()


COMPACTION_THRESHOLD_MESSAGES = 16  # Only compact when history exceeds ~8 conversational turns
COMPACTION_THRESHOLD_CHARS = 8000   # Or when cumulative text exceeds ~2,000 tokens
KEEP_RECENT_MESSAGES = 6            # Retain recent 3 conversational turns untouched


def should_compact(
    history: list,
    threshold_messages: int = COMPACTION_THRESHOLD_MESSAGES,
    threshold_chars: int = COMPACTION_THRESHOLD_CHARS,
) -> bool:
    """Returns True ONLY when conversation history exceeds the length/token threshold."""
    if not history:
        return False
    if len(history) >= threshold_messages:
        return True
    total_chars = sum(len(_extract_role_and_text(m)[1]) for m in history)
    return total_chars >= threshold_chars


def compact_conversation(
    history: list,
    max_messages: int = COMPACTION_THRESHOLD_MESSAGES,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> list:
    """
    Compacts older conversation history into a unified contextual memory summary
    ONLY when the message history is too big (exceeds max_messages or threshold chars).

    Follows industry standard pattern (LangChain ConversationSummaryBufferMemory / OpenAI):
      1. Keeps the most recent `keep_recent` messages intact to preserve short-term flow.
      2. Compiles older messages and any prior summary into a structured transcript.
      3. Calls the active LLM to generate an objective, information-dense memory summary.
      4. Replaces older messages with a concise memory context prefix turn.
      5. Fallbacks gracefully to sliding window truncation if LLM call fails.
    """
    if not should_compact(history, threshold_messages=max_messages):
        return history

    keep_count = max(2, min(keep_recent, len(history) - 2))
    older_messages = history[:-keep_count]
    recent_messages = history[-keep_count:]

    if not older_messages:
        return history

    # Check for existing summary block in the first older message
    existing_summary = ""
    start_idx = 0
    first_role, first_text = _extract_role_and_text(older_messages[0])
    if "[Context from earlier conversation:" in first_text:
        existing_summary = first_text.replace(
            "[Context from earlier conversation:", ""
        ).split("(Keep this background")[0].strip()
        start_idx = 1
        # Skip the acknowledgment assistant message if present
        if len(older_messages) > 1:
            second_role, second_text = _extract_role_and_text(older_messages[1])
            if second_role == "assistant" and "Understood, I remember" in second_text:
                start_idx = 2

    # Build transcript of older messages
    transcript_lines = []
    if existing_summary:
        transcript_lines.append(f"[Previous Summary of Prior Turns]:\n{existing_summary}\n")

    for msg in older_messages[start_idx:]:
        role, text = _extract_role_and_text(msg)
        if not text:
            continue
        speaker = "Akari" if role == "assistant" else "User"
        transcript_lines.append(f"{speaker}: {text}")

    if not transcript_lines:
        return history

    transcript_text = "\n".join(transcript_lines)

    summary_prompt = (
        "You are the memory compaction system for an AI (Akari Watanabe). "
        "Summarize the earlier conversation transcript below into a concise, continuous factual summary (1-2 short paragraphs).\n\n"
        "MANDATORY GUIDELINES:\n"
        "- Retain key personal facts, preferences, names, and information shared by the User.\n"
        "- Retain major topics discussed, questions asked, decisions made, and emotional rapport.\n"
        "- Retain ongoing narrative context needed for future turns.\n"
        "- Do NOT write conversational filler, commentary, or markdown lists.\n"
        "- Output ONLY the clean summary paragraph.\n\n"
        f"TRANSCRIPT TO SUMMARIZE:\n{transcript_text}\n\n"
        "CONCISE SUMMARY:"
    )

    try:
        from .provider import classic_chat

        summary = classic_chat(summary_prompt)
        cleaned_summary = summary.strip()
        if not cleaned_summary or len(cleaned_summary) < 10:
            raise ValueError("Empty or invalid summary returned by model")

        print(
            f"[Compactor] Compacted {len(older_messages)} older messages into summary ({len(cleaned_summary)} chars). "
            f"Preserved {len(recent_messages)} recent messages."
        )

        compacted_msg = UserMessage(
            content=(
                f"[Context from earlier conversation:\n{cleaned_summary}\n"
                "(Keep this background memory in mind while continuing the conversation naturally.)]"
            )
        )
        compacted_ack = AssistantMessage(
            content="[Understood, I remember everything we talked about and will keep that in mind.]"
        )
        return [compacted_msg, compacted_ack] + recent_messages

    except Exception as err:
        print(f"[Compactor] LLM summarization error ({err}). Falling back to sliding window.")
        # Graceful fallback: return recent messages to avoid unbounded token growth
        return recent_messages


async def compact_conversation_async(
    history: list,
    max_messages: int = COMPACTION_THRESHOLD_MESSAGES,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> list:
    """Async wrapper to run compact_conversation only when history exceeds threshold."""
    if not should_compact(history, threshold_messages=max_messages):
        return history

    return await asyncio.to_thread(
        compact_conversation,
        history=history,
        max_messages=max_messages,
        keep_recent=keep_recent,
    )

