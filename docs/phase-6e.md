# Phase 6E — Private cloud synchronization

Cloud synchronization is an authenticated, opt-in feature. It is disabled for every account until the user explicitly enables it from the web Privacy settings or mobile Sync page. Enabling sync does not upload existing local data.

## Contract

- `GET /api/v1/sync/status` reports consent and synchronized account preferences.
- `PATCH /api/v1/sync/consent` enables or disables consent.
- `PATCH /api/v1/sync/preferences` updates locale/theme after consent.
- `POST /api/v1/sync/preview` validates a selected local batch without changing the database.
- `POST /api/v1/sync/import` imports only the selected records.
- `GET /api/v1/sync/changes?cursor=<cursor>&limit=<n>` returns private, cursor-paginated changes.

Only `translation` and `favorite` records are accepted. Audio, images, and documents are rejected by the schema boundary and are not part of the synchronization model. Batches are capped at 50 records and 256 KiB. The API derives the account from the authenticated session; no client `user_id` is accepted.

Each local record has a stable client record ID. The server creates its own UUID and stores a per-user synchronization ledger in `sync_records`. Repeating an import with the same record ID is safe. Conflicts use last-write-wins by `client_updated_at`; equal timestamps use the canonical payload SHA-256 hash as a deterministic tie-breaker. Deletes remain as server-side tombstones, so stale offline writes cannot resurrect deleted records.

## Privacy and logout

Local preview and selection are required before upload. There is no background upload. Mobile retry entries contain only selected translation/favorite payloads and the authenticated user ID; they are cleared on logout or account change. The server stores explicitly synchronized translation text as private, user-owned account data, never raw audio/image/document data.

The migration is `0010_private_sync`. Apply it with:

```bash
cd services/api
alembic upgrade head
```

Use HTTPS for deployed clients. A disabled sync consent blocks preview, import, and change retrieval with `SYNC_CONSENT_REQUIRED`.
