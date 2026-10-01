# AWS Bedrock Bearer Token & Mantle Integration

**Date:** 2026-10-02  
**Status:** Implemented & Verified  
**Related Files:**  
- `./server/.env`
- `./server/src/llm/bedrock_model.py`
- `./server/src/llm/provider.py`
- `./client/src/navigation/useNavigation.ts`
- `./client/src/components/screens/SettingsScreen.tsx`
- `./client/src/components/ChatInput.tsx`
- `./client/src/networking/AvatarSocket.ts`

---

## 1. Overview & Objective

AWS Bedrock API keys (`bedrock-api-key-...`) allow authenticating requests to Amazon Bedrock using an **HTTP Bearer token** (`Authorization: Bearer <key>`) instead of standard AWS IAM Signature Version 4 (SigV4) credentials.

This integration connects the assistant to **Amazon Bedrock Mantle**, an OpenAI-compatible distributed inference plane hosted on AWS infrastructure (`https://bedrock-mantle.{region}.api.aws/v1`), providing seamless chat completion, fast token streaming, and function calling (tool calling).

---

## 2. Authentication & Endpoint Architecture

### Bearer Token Format
The Bedrock API key is stored in the environment variable:
```env
AWS_BEARER_TOKEN_BEDROCK="bedrock-api-key-YmVkcm9jay..."
```
Inside the base64-encoded key is an action descriptor (`Action=CallWithBearerToken`) and the AWS region (e.g. `ap-south-1`).

### Endpoint Routing
- **Base URL:** `https://bedrock-mantle.{region}.api.aws/v1`
- **Region Detection:** Inferred automatically from `AWS_REGION`, `BEDROCK_REGION`, or decoded directly from the bearer token credential (defaulting to `ap-south-1`).
- **Client:** Configured using the standard `openai.OpenAI` Python SDK with `base_url` pointing to the Mantle endpoint and `api_key` set to the bearer token.

---

## 3. Supported Bedrock Models

The following high-performance foundation models are available and verified on Bedrock Mantle:

| Model ID | Display Name | Tool Calling | Vision Native | Context Window |
|---|---|---|---|---|
| `mistral.ministral-3-8b-instruct` | **Ministral 3 8B (Default)** | Supported | Vision-assisted | 128k |
| `google.gemma-3-4b-it` | **Google Gemma 3 4B (Fast)** | Supported | Vision-assisted | 32k |
| `google.gemma-3-12b-it` | **Google Gemma 3 12B** | Supported | Vision-assisted | 32k |
| `qwen.qwen3-32b` | **Qwen 3 32B** | Supported | Vision-assisted | 32k |
| `deepseek.v3.1` | **DeepSeek V3.1** | Disabled | Vision-assisted | 64k |
| `mistral.ministral-3-14b-instruct` | **Ministral 3 14B** | Supported | Vision-assisted | 128k |
| `mistral.mistral-large-3-675b-instruct`| **Mistral Large 3 675B** | Supported | Vision-assisted | 128k |
| `openai.gpt-oss-120b` | **OpenAI GPT-OSS 120B (Reasoning Flagship)** | Supported | Vision-assisted | 128k |
| `openai.gpt-oss-20b` | **OpenAI GPT-OSS 20B (Fast Reasoning)** | Supported | Vision-assisted | 128k |
| `anthropic.claude-sonnet-5` | **Claude Sonnet 5** | Supported | Vision-assisted | 200k |
| `anthropic.claude-opus-5` | **Claude Opus 5 (Flagship)** | Supported | Vision-assisted | 200k |

*Note: For vision inputs, when `vision_supported` is False, the server automatically passes the image to the background vision feature extractor and prepends `[Image description: ...]` to the prompt.*

---

## 4. Key Learnings & Nuances

1. **`bedrock-runtime` vs. `bedrock-mantle`:**
   - Calling the traditional `bedrock-runtime` Converse API directly with a bearer token can throw `ValidationException: Operation not allowed` on accounts lacking standard IAM marketplace agreements.
   - Calling `bedrock-mantle.{region}.api.aws/v1` via OpenAI-compatible REST endpoints executes cleanly with full tool calling, streaming, and high throughput.
2. **Tool Calling Compatibility:**
   - Bedrock Mantle natively understands OpenAI's `tools` and `tool_choice` format, returning structured function call deltas (`delta.tool_calls`) that parse with existing tool execution loops.
3. **Anthropic Claude 5 Mantle Status (404 Not Found):**
   - In `client.models.list()`, Amazon Bedrock Mantle advertises `anthropic.claude-opus-5` and `anthropic.claude-sonnet-5`.
   - However, when queried via `/v1/chat/completions`, AWS Bedrock returns HTTP 404 (`{'code': 'not_found_error', 'message': 'not found'}`) because AWS has not yet deployed or enabled the chat completion runtime endpoints for these models in the active region (`ap-south-1`).
   - Claude Opus 5 and Sonnet 5 are retained in the UI marked as `Preview`. When selected, the backend gracefully catches 404s and informs the user to select an active model (e.g. `ministral.ministral-3-8b-instruct`, `openai.gpt-oss-120b`, `google.gemma-3-4b-it`, `qwen.qwen3-32b`).
4. **Token Detection & UI Status:**
   - The UI Settings screen connects to the backend WebSocket and requests config via `get_config`.
   - When `AWS_BEARER_TOKEN_BEDROCK` is detected in `./server/.env`, the backend reports `"bedrock": true` in `api_keys_configured`.
   - The Settings screen displays `Token Active` with a green indicator, pre-populates the input placeholder with `Configured in server .env (AWS_BEARER_TOKEN_BEDROCK)`, and provides visual confirmation that inference is ready.
   - If the user saves a token locally in the browser, `AvatarSocket` synchronizes `akari_bedrock_bearer_token` automatically upon connection.
