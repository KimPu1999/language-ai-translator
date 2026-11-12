# Phase 6B — Profiles, History and Favorites

Phase 6B adds authenticated account data APIs. Every endpoint below requires a
valid Phase 6A session and derives the user identity from that session; clients
cannot submit a `user_id` to select an account.

## Account data

- `GET/PATCH /api/v1/profile` reads and updates the display name. Email changes
  remain verification-sensitive and are not accepted by this phase.
- `GET/PATCH /api/v1/preferences` manages locale, theme, and the explicit
  `history_enabled` privacy opt-in.
- `GET /api/v1/account/export` returns JSON containing the account profile,
  preferences, owned history, favorites, and authenticated document metadata.
- `DELETE /api/v1/account` requires the current password as recent
  reauthentication. It deletes the account only after owned document files are
  cleaned up, revokes sessions, and removes account-linked history, favorites,
  preferences, action tokens, and authenticated document jobs.

## History and favorites

History is never written by translation requests. A client must first set
`history_enabled=true`, then explicitly call `POST /api/v1/history`. History
and favorites are filtered by the authenticated user on every query and
mutation. Pagination uses `limit` (1–100) and `offset`; history also supports
source/target language and text search filters.

Favorites reference an owned history translation. A user cannot favorite,
read, or delete another user's translation or favorite.

## Document ownership

Phase 5 document-job routes now accept authenticated sessions and derive an
owner subject as `user:<uuid>`. Invalid sessions do not fall back to the
development guest capability token. Guest document jobs remain disabled by
default and are restricted to development when explicitly enabled.

Metadata-only provider usage events are retained for operational accounting;
they do not contain account identity or raw user text. No new automatic
translation history persistence was introduced.
