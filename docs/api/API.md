# REST & WebSocket API Specification — ScanSocial

Base URL: `http://127.0.0.1:{PORT}/api/v1`  
Required Authentication Header: `X-App-Session-Token: {TOKEN}`

## 1. Scan Engine Endpoints
- `POST /scans`: Creates and starts a new discovery scan job.
  - Body: `{ "platform": "FACEBOOK", "keywords": ["cần lắp wifi"], "max_posts": 500, "max_age_hours": 12, "blacklist_mode": "IGNORE_HARD" }`
  - Returns: `{ "job_id": "...", "status": "RUNNING", "started_at": "..." }`
- `GET /scans/{id}`: Returns status, counts (`scanned`, `matched`, `qualified`, `spam`, `errors`).
- `POST /scans/{id}/pause`: Pauses active scanning.
- `POST /scans/{id}/resume`: Resumes paused scanning.
- `POST /scans/{id}/stop`: Gracefully terminates the scan job.
- `GET /posts`: Paginated query with filters (`lead_score_min`, `has_phone`, `is_raw`, `keyword`, `search`).
- `GET /posts/{id}`: Full post L1 payload including score breakdown, extracted phones, and author details.
- `GET /posts/{id}/comments`: Fetches L2 comments for the post.

## 2. CRM & Person Endpoints
- `GET /persons`: List person contacts with pagination and quality filter.
- `GET /persons/{id}`: Returns unified person profile with phones, social accounts, and timeline.
- `POST /persons`: Manual creation of a person record.
- `POST /persons/{id}/convert-customer`: Promotes person to customer with initial need profile and opportunity.
- `POST /persons/merge`: Merges a duplicate person into a primary record with audit logging.
- `GET /customers/{id}`: Comprehensive Customer 360 view.
- `PUT /customers/{id}/need-profile`: Updates structured need profile.

## 3. Care Calendar
- `GET /care-tasks`: Retrieves care tasks filtered by date range (`today`, `week`, `overdue`) or status.
- `POST /care-tasks`: Creates a new follow-up or care task.
- `PATCH /care-tasks/{id}/complete`: Marks a task completed and updates customer interaction timestamp.

## 4. Global Search
- `GET /search?q={query}&type={optional}`: Sub-second FTS5 query across phones, URLs, names, notes, and post text.

## 5. WebSocket Live Feed
- Connection: `ws://127.0.0.1:{PORT}/ws/live?token={TOKEN}`
- Broadcast events:
  - `POST_DISCOVERED`
  - `SCAN_PROGRESS`
  - `LEAD_QUALIFIED`
  - `SCAN_COMPLETED`
  - `CARE_TASK_DUE`
