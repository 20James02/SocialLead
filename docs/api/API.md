# Implemented API

Base: `http://127.0.0.1:{PORT}/api/v1`. REST requires `X-App-Session-Token`. See `/docs` or `/openapi.json` on the running engine for exact request/response schemas.

Routes below are generated from the application. No authentication-free data endpoint is provided. `/health` only reports engine readiness.

| Method | Path | Operation |
| --- | --- | --- |
| GET | `/api/v1/scans` | List Jobs |
| POST | `/api/v1/scans` | Create Scan Job |
| POST | `/api/v1/scans/import` | Import Posts |
| GET | `/api/v1/scans/{job_id}` | Get Scan Job |
| POST | `/api/v1/scans/{job_id}/pause` | Pause Scan Job |
| POST | `/api/v1/scans/{job_id}/resume` | Resume Scan Job |
| POST | `/api/v1/scans/{job_id}/stop` | Stop Scan Job |
| GET | `/api/v1/posts` | List Posts |
| GET | `/api/v1/posts/{post_id}` | Get Post Detail |
| POST | `/api/v1/posts/{post_id}/save` | Save Post |
| DELETE | `/api/v1/posts/{post_id}/save` | Unsave Post |
| GET | `/api/v1/posts/{post_id}/analysis` | Post Analysis |
| GET | `/api/v1/posts/{post_id}/comments` | Post Comments |
| POST | `/api/v1/posts/{post_id}/promote` | Promote Post |
| POST | `/api/v1/posts/{post_id}/sync-comments` | Sync Post Comments |
| POST | `/api/v1/posts/{post_id}/comments/{comment_id}/promote` | Promote Comment |
| GET | `/api/v1/persons` | List Persons |
| POST | `/api/v1/persons` | Create Person |
| POST | `/api/v1/persons/{person_id}/convert-customer` | Convert Person To Customer |
| POST | `/api/v1/persons/merge` | Merge Persons |
| GET | `/api/v1/customers/{customer_id}` | Get Customer 360 |
| GET | `/api/v1/care-tasks` | List Care Tasks |
| POST | `/api/v1/care-tasks` | Create Care Task |
| PATCH | `/api/v1/care-tasks/{task_id}/complete` | Complete Care Task |
| GET | `/api/v1/search` | Search Global |
| POST | `/api/v1/backup/create` | Create Backup |
| GET | `/api/v1/backup` | List Backups |
| POST | `/api/v1/backup/restore` | Restore Backup |
| GET | `/api/v1/persons/{person_id}` | Person Detail |
| PATCH | `/api/v1/persons/{person_id}` | Edit Person |
| POST | `/api/v1/persons/{person_id}/notes` | Create Note |
| PUT | `/api/v1/persons/{person_id}/labels` | Set Labels |
| PUT | `/api/v1/persons/{person_id}/permission` | Set Permission |
| GET | `/api/v1/customers` | List Customers |
| PATCH | `/api/v1/customers/{customer_id}/status` | Customer Status |
| PUT | `/api/v1/customers/{customer_id}/need-profile` | Update Need |
| POST | `/api/v1/customers/{customer_id}/opportunities` | Create Opportunity |
| PATCH | `/api/v1/opportunities/{opportunity_id}` | Update Opportunity |
| GET | `/api/v1/blacklist` | List Blacklist |
| POST | `/api/v1/blacklist` | Create Blacklist |
| DELETE | `/api/v1/blacklist/{rule_id}` | Delete Blacklist |
| GET | `/api/v1/care-tasks/proposals` | Followup Proposals |
| GET | `/api/v1/dashboard` | Dashboard |
| GET | `/api/v1/export/customers` | Export Customers |
| GET | `/api/v1/conversations` | List Conversations |
| POST | `/api/v1/conversations` | Create Conversation |
| GET | `/api/v1/conversations/{conversation_id}/messages` | Get Messages |
| POST | `/api/v1/conversations/{conversation_id}/messages` | Log Message |
| POST | `/api/v1/conversations/{conversation_id}/suggestion` | Suggest Reply |
| GET | `/api/v1/integrations` | Integration Status |
| PUT | `/api/v1/integrations/{provider}/token` | Set Token |
| DELETE | `/api/v1/integrations/{provider}/token` | Delete Token |
| GET | `/api/v1/campaigns` | List Campaigns |
| POST | `/api/v1/campaigns` | Create Campaign |
| GET | `/api/v1/campaigns/{campaign_id}/preview` | Preview Campaign |
| PATCH | `/api/v1/campaigns/{campaign_id}/recipients/{recipient_id}/reconcile` | Reconcile Delivery |
| POST | `/api/v1/campaigns/{campaign_id}/recipients/{recipient_id}/send` | Send Reviewed |
| GET | `/health` | Health Check |

WebSocket: `/ws/live?token={TOKEN}`. Authentication failure closes with policy violation. Live events refresh scanner progress and care reminders; clients reconnect and reload authoritative REST data.

Facebook discovery is restricted to authorized Page feeds; Threads uses official keyword search. `/posts/{post_id}/comments` reads stored comments; `/posts/{post_id}/sync-comments` explicitly requests provider updates. `/scans/import` accepts data the operator is authorized to use.

OA previews return recipient eligibility. Reviewed send can yield SENT, REJECTED or UNKNOWN. UNKNOWN is not a success and must be reconciled with a note before further sends. Personal Zalo endpoints record manually entered conversations/messages and produce drafts.
