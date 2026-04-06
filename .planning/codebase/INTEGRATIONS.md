# INTEGRATIONS.md — External Services & APIs

## Telegram (via Telethon 1.36.0)

| API | Used In | Purpose |
|-----|---------|---------|
| `contacts.SearchRequest` | `PromotionEngine.search_groups()`, `ForwardEngine._phase_search()` | Global keyword group discovery |
| `messages.SearchGlobalRequest` | `PromotionEngine.search_groups()` | Secondary group discovery via post search |
| `channels.JoinChannelRequest` | `PromotionEngine.join_group()`, `ForwardEngine._phase_join()` | Join public groups/channels |
| `client.send_message()` | `PromotionEngine.send_message()`, `ForwardEngine._phase_forward_loop()` | Send promotional messages |
| `client.action()` ("typing") | Both engines | Human-like typing simulation before send |
| `client.connect()` / `client.is_user_authorized()` | `AccountsTab._async_login()` | Session management |
| `client.send_code_request()` | `AccountsTab._async_login()` | OTP (SMS) auth flow |
| `client.sign_in()` | `AccountsTab._async_login()` | Complete sign-in with OTP/2FA |

## Telethon Error Handling

All Telegram errors are explicitly caught per-operation:

| Error Class | Handling |
|-------------|---------|
| `FloodWaitError` | Wait `e.seconds` (capped at 60s in controller), retry or requeue |
| `SlowModeWaitError` | Return `SlowMode:<seconds>` error string |
| `PeerFloodError` | Mark as failed — too many send attempts |
| `ChatWriteForbiddenError` | Skip group permanently |
| `UserBannedInChannelError` | Skip group permanently |
| `UserNotParticipantError` | Skip group permanently |
| `ChannelPrivateError` | Skip group permanently |
| `SessionPasswordNeededError` | Prompt user for 2FA password in `OtpDialog` |
| `UsernameInvalidError` | Imported but not yet actively used |
| `UsernameNotOccupiedError` | Imported but not yet actively used |

## Telegram Authentication Flow

1. User enters phone + API credentials in `AddAccountDialog`
2. `AccountsTab._async_login()` calls `client.send_code_request()`
3. `OtpDialog` displayed — user enters OTP (and optional 2FA password)
4. `client.sign_in()` called — on `SessionPasswordNeededError`, password used
5. Telethon persists session to `data/session_<phone>.session` file
6. `Account.client` holds the active `TelegramClient` reference in-memory

## No External Third-Party Services

- No databases (no SQLite via SQLAlchemy, no Redis, no Postgres)
- No REST APIs (no HTTP clients beyond Telegram)
- No auth providers (no OAuth, no JWT)
- No cloud services (AWS, GCP, etc.)
- No webhooks
- All state is local JSON files
