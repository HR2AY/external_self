# Context Sources and Schema

## Bundled application binding

- Bundled app root: `<skill-directory>/assets/trajectory-app`
- Bundled FACT source: `<skill-directory>/assets/trajectory-app/data/places.json`
- Bundled BACKGROUND source: `<skill-directory>/assets/trajectory-app/data/BACKGROUND.md`
- Bundled INFERENCE source: `<skill-directory>/assets/trajectory-app/data/INFERENCE.md`
- Frontend read endpoint: `GET /api/places`
- Frontend write endpoint: `PUT /api/places`

The `.skill` package contains this application and its current JSON snapshot. After extraction or installation, run it from the bundled app root with `npm ci` followed by `npm run dev`.

## Separate active project binding

When a separate trajectory project is active, locate these files relative to that project rather than assuming an absolute machine-specific path:

- FACT source: `<project-root>/data/places.json`
- Optional BACKGROUND source: `<project-root>/data/BACKGROUND.md`
- Optional INFERENCE source: `<project-root>/data/INFERENCE.md`
- Frontend read endpoint: `GET /api/places`
- Frontend write endpoint: `PUT /api/places`

For retrieval and research, the skill may read either in-scope JSON directly or use the GET endpoint when the local app is running. It must never use the PUT endpoint or write a FACT JSON. Explicit node editing in the map application is a separate user-authorized product action.

If a separate project is active, locate its `data/places.json` from the current workspace and pass its path to the retriever with `--data`. Otherwise the retriever falls back to the bundled snapshot.

## Host capabilities

Use whichever equivalent search, browser, terminal, and local-file capabilities the host provides. The Skill does not depend on a specific provider response schema. If the host cannot display a particular media type inline, use its native preview or a verified clickable thumbnail/link.

## Observed FACT JSON schema

The source is a JSON array. Each item currently has this shape:

```json
{
  "id": 1789791022692,
  "name": "汉口，江岸区、江汉区",
  "city": "武汉",
  "timePoint": "2005-02-04",
  "durationYears": 10,
  "event": "出生、度过小学童年时光",
  "longitude": 114.28205530021165,
  "latitude": 30.611286072901805
}
```

Equivalent constraints:

| Field | Type | Meaning |
|---|---|---|
| `id` | number | Stable local node identifier |
| `name` | string | User-entered place or node name |
| `city` | string | City; may be empty |
| `timePoint` | string | Start date in `YYYY-MM-DD` form |
| `durationYears` | number | Approximate duration in years; may be fractional or zero |
| `event` | string | User-entered event and life-stage context; may be empty |
| `longitude` | number | Map longitude |
| `latitude` | number | Map latitude |

All fields are FACT because the user explicitly entered them. Empty values remain facts about missingness; do not fill them by inference.

## Time interpretation

Treat `timePoint` as the node's start. Treat `durationYears` as approximate, not precise calendar arithmetic. A node starting in 2005 with duration 10 years can anchor roughly 2005–2015. Preserve uncertainty when the user's wording or data is approximate.

## BACKGROUND MD

BACKGROUND contains later-learned user-provided context about a life stage. It is not part of the map schema and does not become FACT JSON.

Recommended entry form:

```markdown
## Background: short title
- Related nodes: 1789791022692
- Period: 2005–2015
- Place: 武汉
- Source: user statement in conversation, with date if available

User-provided background text.
```

## INFERENCE MD

INFERENCE contains model-derived relationships. It remains inference even if persuasive and must never migrate into FACT or BACKGROUND.

Recommended entry form:

```markdown
## Inference: short title
- Related nodes: 1789791022692, 1789790962253
- Status: hypothesis | supported inference
- Evidence: source identities or citations
- Created: YYYY-MM-DD

Reasoning, uncertainty, and disconfirming evidence.
```

## Frontend data flow

The React app fetches `GET /api/places` on startup. Vite's local middleware reads `data/places.json`. Frontend add/edit/delete operations send the full array to `PUT /api/places`, which atomically replaces the file through a temporary file.

That write path belongs to explicit user editing in the map UI. It is outside this Skill's authority.

## Project runtime

From either the source project root or bundled app root:

```text
npm ci
npm run dev
```

Vite serves the frontend and local JSON API, normally at `http://localhost:5173/`.

Production build check:

```text
npm run build
```
