# Tool Calling Architecture, Model Capability Matrix & Streaming Integration Specification
**Date**: September 26, 2026  
**Repository**: `Lakshyakumar266/anime-wifu-companion` (`AkariWattnabe-companion`)  
**Feature**: Tool Calling / Function Calling Capability Subsystem  
    
---

## 1. Overview & Objective

This specification formalizes the architecture, discovery patterns, provider compatibility matrix, execution mechanics, and user interface controls implemented for the **Tool Calling** (Function Calling) feature in Akari Watanabe companion.

Reference Codebase Links:
- `./server/src/tools/base.py`
- `./server/src/tools/builtins.py`
- `./server/src/tools/registry.py`
- `./server/src/tools/__init__.py`
- `./server/src/llm/mistral_model.py`
- `./server/src/llm/freeai_model.py`
- `./server/src/llm/provider.py`
- `./server/src/chat/loop.py`
- `./server/src/bridge/websocket_server.py`
- `./server/src/bridge/events.py`
- `./client/src/components/screens/SettingsScreen.tsx`
- `./client/src/components/screens/SettingsScreen.css`
- `./client/src/components/ChatInput.tsx`
- `./client/src/components/ChatInput.css`
- `./client/src/navigation/useNavigation.ts`
- `./client/src/networking/AvatarSocket.ts`
- `./client/src/networking/types.ts`
- `./docs/plans/tool-calling-02.md`

---

## 2. End-to-End Pipeline & Execution Lifecycle

Instead of treating tool results as spoken dialog or robotic JSON output, Akari employs a **Two-Stage Conversational Loop**:

```text
User Message (Browser UI)
    ↓
Check: Is Tool Calling Enabled & Supported?
    ├── NO  → Standard Low-Latency Token Stream → Dialogue Chunker → TTS → VRM
    └── YES → Stage 1: Tool Decision & Execution Loop
                   ↓
              Model requests tool_call (e.g. get_current_time)
                   ↓
              Broadcast `tool_start` → UI shows "Checking current time..."
                   ↓
              Tool Registry executes function safely with timeout
                   ↓
              Broadcast `tool_end` → Append ToolMessage to conversation
                   ↓
              Can model repeat? (Up to MAX_TOOL_CALL_ROUNDS=5)
                   ↓
              Stage 2: Final Natural Response Generation
                   ↓
              Emits Tsundere response with emotion tag (e.g. [happy], [neutral])
                   ↓
              Dialogue Chunker (. ! ? or 16 words)
                   ↓
              TTS Engine (Fish Audio / GPT-SoVITS WAV bytes)
                   ↓
              AudioPlayer (Web Audio API) + LipSyncController (RMS 60fps) + VRM expressions
```

### Critical Behavioral Guarantees
1. **No Robotic Tool Speech**: Raw tool JSON payloads and internal function names are strictly isolated from the TTS synthesizer and subtitle rendering. Only the final conversational response is vocalized.
2. **Zero Hallucination Grounding**: If the model needs real-time context (such as time, date, or system status), it relies on verified tool outputs. If a tool fails or times out, the error is passed back to the model context so Akari explains naturally rather than inventing false facts.
3. **Persona Preservation**: Akari retains her Tsundere gyaru personality throughout:
   - Example user prompt: *"What time is it?"*
   - Model tool execution: `get_current_time` $\to$ `{"time_12h": "4:41 PM", ...}`
   - Akari response: `"[neutral] Ugh, four forty-one? Already? I swear, time just flies when I'm around you. You should probably stop wasting time and do something useful..."`

---

## 3. Provider & Model Capability Matrix

Tool calling is treated as a **first-class capability flag** at both provider and individual model levels. The application does not assume all models support function calling.

| Provider | Model ID | Tool Calling Supported | Technical Notes |
| :--- | :--- | :---: | :--- |
| **Mistral AI** | `ministral-8b-latest` | **Yes** | Full native JSON schema function calling via official Mistral SDK (`mistralai>=2.8.0`). Default model. |
| **Mistral AI** | `mistral-small-latest` | **Yes** | Large context reasoning with tool calling support. |
| **Mistral AI** | `open-mistral-7b` | **Yes** | Mistral 7B open weights with function calling support. |
| **Free.ai** | `qwen7b` | **Yes** | Qwen 2.5 7B natively parses OpenAI-compatible `tools` array. Free gateway tier. |
| **Free.ai** | `qwen3-8b` | **Yes** | Qwen 3 8B instruction-tuned model supporting function calling. |
| **Free.ai** | `mistral` | **No** | Endpoint on gateway does not serve function calling endpoints for this alias. |
| **Free.ai** | `deepseek-r1` | **No** | Reasoning / Chain of Thought model; does not support function calling on this endpoint. |

### Settings UI Model-Switching Guarantee
When switching between models in `./client/src/components/screens/SettingsScreen.tsx`:
- Selecting a model with `toolCallingSupported: false` immediately disables the tool toggle and sets the badge to **Model Unsupported**.
- The backend WebSocket server validates every request in `./server/src/bridge/websocket_server.py`; even if a client attempts to forge a `set_tool_calling` payload with an incompatible model, the server rejects it and keeps tools disabled.

---

## 4. Built-in Tools Specification (`./server/src/tools/`)

All tools are strictly allowlisted and execute in an asynchronous, non-blocking thread pool with timeout bounds.

### 4.1 Tool 1: `get_current_time`
- **Identifier**: `get_current_time`
- **Display Name**: Current Time
- **Description**: Returns current time and date for any city, country, or timezone worldwide (e.g. Tokyo, London, New York, Paris, India, PST, UTC). Defaults to user's local time if omitted.
- **Parameters**:
  - `location` (optional string): Target city, country, or timezone name.
  - `timezone` (optional string): Target timezone code or IANA identifier.
- **Output Sample**:
  ```json
  {
    "status": "success",
    "location": "Tokyo",
    "time_12h": "8:30 PM",
    "time_24h": "20:30:45",
    "date": "Saturday, September 26, 2026",
    "timezone_name": "JST",
    "utc_offset": "UTC+09:00",
    "is_morning": false,
    "is_evening": true
  }
  ```

### 4.2 Tool 2: `get_timezone_info`
- **Identifier**: `get_timezone_info`
- **Display Name**: Timezone Details
- **Description**: Returns detailed timezone metadata including IANA timezone code, UTC offset (e.g. UTC+05:30), daylight saving status, and current time for any location or user's local timezone.
- **Parameters**: `location` (optional string).

### 4.3 Tool 3: `convert_time`
- **Identifier**: `convert_time`
- **Display Name**: Timezone Converter
- **Description**: Converts a specific time from one timezone/city to another (e.g. '3:00 PM' from 'New York' to 'Tokyo'). Handles day offsets and time differences without hallucination.
- **Parameters**:
  - `time_str` (string, required): e.g. "3:00 PM", "15:30", "noon".
  - `from_location` (string, required): Source location.
  - `to_location` (string, required): Destination location.
  - `date_str` (optional string): Reference date.

### 4.4 Tool 4: `time_difference`
- **Identifier**: `time_difference`
- **Display Name**: Time Difference
- **Description**: Calculates exact current time difference and compares time between two cities, countries, or timezones.
- **Parameters**: `location_a` (string, required), `location_b` (string, required).

### 4.5 Tool 5: `get_current_date`
- **Identifier**: `get_current_date`
- **Display Name**: Current Date
- **Description**: Returns current calendar date, day of the week, month, year, and day of the year for any timezone.
- **Parameters**: `location` (optional string).

### 4.6 Tool 6: `get_day_of_week`
- **Identifier**: `get_day_of_week`
- **Display Name**: Day of Week
- **Description**: Calculates the weekday, formatted calendar date, and days relative to today for any past, present, or future date.
- **Parameters**: `date_str` (string, required), `location` (optional string).

### 4.7 Tool 7: `calculate`
- **Identifier**: `calculate`
- **Display Name**: Calculator
- **Description**: Safe AST mathematical expression evaluator for arithmetic, percentages (`25% of 400`), powers, and functions (`sqrt`, `abs`, `round`, `sin`, `cos`). Strictly avoids unsafe Python `eval()`.
- **Parameters**: `expression` (string, required).

### 4.8 Tool 8: `get_system_status`
- **Identifier**: `get_system_status`
- **Display Name**: System Status
- **Description**: Returns host OS environment, Python runtime version, active AI model, detected client timezone, and companion health metrics.
- **Parameters**: `{ "type": "object", "properties": {}, "required": [] }`

---

## 5. Streaming Mechanics with Tool Calling

### 5.1 Mistral Client Streaming Loop
In `./server/src/llm/mistral_model.py`:
1. The stream is initiated with `client.chat.stream(model=active_model, messages=messages, tools=tools)`.
2. As chunks arrive, `choice.delta.tool_calls` chunks are checked:
   - If present, tool IDs, function names, and JSON argument fragments are collected in an in-memory dictionary.
   - If normal text tokens (`choice.delta.content`) arrive instead, they are immediately yielded to downstream dialogue chunkers without delay.
3. When `finish_reason == "tool_calls"`:
   - Tool arguments are parsed and executed via `./server/src/tools/registry.py`.
   - `AssistantMessage(content="", tool_calls=...)` and `ToolMessage(tool_call_id=..., name=..., content=...)` are appended to the conversation history.
   - The loop iterates (bounded by `max_tool_rounds=5`) to allow the model to either request additional tools or stream the final answer.

### 5.2 Multi-Tool Execution in a Single Turn
The model can invoke multiple tools either in parallel or sequentially. For example, for the query *"What is today's date and what time is it?"*, the model invokes both `get_current_date` and `get_current_time` in round 1, then synthesizes both results in round 2:
```text
Round 1: [Tool: get_current_date] → Saturday, September 26, 2026
Round 1: [Tool: get_current_time] → 4:41 PM
Round 2: [happy] Ooooh, Saturday already? That means we have all day to hang out, right? It's 4:41 PM now...
```

---

## 6. Interrupt & Stop Handling

If the user clicks **Stop** in `./client/src/components/ChatInput.tsx` while a tool is being evaluated or executed:
1. Client sends binary packet `0x03` (`AUDIO_INTERRUPT`) and JSON `{"type": "interrupt"}`.
2. `stop_chat_stream()` in `./server/src/chat/loop.py` triggers `cancel_event.set()` (a thread-safe `threading.Event`).
3. Both `mistral_model.py` and `freeai_model.py` check `cancel_event.is_set()` before and after every tool execution and token chunk.
4. Any active tool task or LLM stream terminates immediately, cleaning up audio queues and returning the UI to idle state.

---

## 7. Frontend Settings UI & URL Synchronization

### 7.1 Settings Screen Controls (`./client/src/components/screens/SettingsScreen.tsx`)
1. **Master Toggle**:
   - High-contrast glassmorphic toggle with ON/OFF indicator.
   - Disabled and dimmed when an unsupported model is active.
2. **Capability Badge**:
   - `MODEL SUPPORTED` (emerald glow) or `MODEL UNSUPPORTED` (amber/ruby warning).
3. **Available Tools Grid**:
   - Visual cards for `Current Time`, `Current Date`, and `System Status`.
   - Cards switch from `Dormant` to `Ready` when tool calling is enabled.
4. **URL Synchronization**:
   - Synchronizes state to URL parameter: `&tools=true` or `&tools=false`.
   - Restores state on browser reload or link sharing.
   - Persists state in `localStorage("akari_tool_calling_enabled")`.

### 7.2 Real-Time Tool Activity Feedback (`./client/src/components/ChatInput.tsx`)
When a tool is invoked by Akari, the server dispatches `{"type": "tool_start", "tool": "get_current_time"}`. The chat input displays an animated status pill:
```text
[ ● Checking current time… ]
```
When tool execution concludes, `tool_end` clears the status pill smoothly as spoken audio begins.

---

## 8. Key Architectural Learnings & Hardening

1. **Windows Python `zoneinfo` Dependency (`tzdata`)**:
   - Python's standard `zoneinfo` module relies on the system timezone database. On Linux/macOS, `/usr/share/zoneinfo` is provided by the OS. On Windows, Python raises `ModuleNotFoundError: No module named 'tzdata'` unless the `tzdata` package is installed. Adding `tzdata` to `pyproject.toml` guarantees reliable cross-platform timezone loading.
2. **Client-Driven Timezone Context Injection**:
   - Because the backend server may run locally, in a remote Docker container, or in the cloud, resolving "local time" by server system clock alone causes discrepancies if the user is in a different timezone. The browser resolves its exact IANA timezone (`Intl.DateTimeFormat().resolvedOptions().timeZone`) and dispatches it in each `chat_message` over WebSocket. The backend sets client context so queries like *"what time is it in my timezone?"* or *"what is the time here?"* always match the user's physical environment.
3. **Safe AST Evaluation vs. Arbitrary Code Execution**:
   - For mathematical calculations, LLMs frequently make simple arithmetic and percentage calculation errors. Rather than invoking dangerous Python `eval()` or `exec()`, the `calculate` tool uses Python's `ast` parser to strictly evaluate mathematical expression nodes with safe operators and white-listed math functions.
4. **Explicit Tool Prompt Grounding**:
   - Instruction-tuned LLMs often exhibit an "overconfidence bias", preferring to guess or invent times rather than triggering tool calls unless system prompts explicitly instruct them that tools must be used for time, date, time differences, and numerical calculations. Grounding the system prompt in `./server/src/prompts/system_prompt_akari.py` ensures consistent, deterministic tool invocations.

