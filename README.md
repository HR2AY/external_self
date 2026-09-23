# External Self

External Self is a deployable Codex Skill for using a person's read-only life trajectory as an anchor for two kinds of discovery:

- **Historical Evidence Retrieval**: finds concrete, contemporaneous traces from the time and place in which the person lived.
- **Contemporary Serendipity Retrieval**: finds evidence-backed connections across multiple life nodes and present interests.

The repository also contains a local React and MapLibre trajectory map, JSON persistence, a lightweight context retriever, and rules for showing verified images and videos beside each discovery.

## Agent deployment contract

An installing Agent should complete the deployment end to end. Do not ask the user to manually copy individual files unless filesystem access is unavailable.

The required installed entry point is:

```text
<CODEX_HOME>/skills/external-self/SKILL.md
```

Resolve `<CODEX_HOME>` from the `CODEX_HOME` environment variable. If it is unset, use the platform default:

- Windows: `%USERPROFILE%\.codex`
- macOS/Linux: `$HOME/.codex`

### Fresh installation

1. Confirm that Git, Python 3.10 or newer, and Node.js with npm are available.
2. Clone this repository so the repository root becomes `<CODEX_HOME>/skills/external-self`.
3. Run the Skill validator when the host provides one.
4. Run the read-only retrieval smoke test.
5. Install frontend dependencies and build the bundled map.
6. Report the installed path and validation results. A new Codex conversation may be required before automatic Skill discovery refreshes.

Windows PowerShell example:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$target = Join-Path $codexHome 'skills\external-self'
git clone https://github.com/HR2AY/external_self.git $target

python (Join-Path $target 'scripts\retrieve_context.py') `
  --data (Join-Path $target 'assets\trajectory-app\data\places.json') `
  --query '上海 2019 求学' --mode relevant --limit 2

Push-Location (Join-Path $target 'assets\trajectory-app')
npm ci
npm run build
Pop-Location
```

macOS/Linux example:

```bash
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
TARGET="$CODEX_HOME/skills/external-self"
git clone https://github.com/HR2AY/external_self.git "$TARGET"

python3 "$TARGET/scripts/retrieve_context.py" \
  --data "$TARGET/assets/trajectory-app/data/places.json" \
  --query "上海 2019 求学" --mode relevant --limit 2

cd "$TARGET/assets/trajectory-app"
npm ci
npm run build
```

### Upgrade an existing installation

The following files may contain private user data and must never be overwritten by repository examples:

```text
assets/trajectory-app/data/places.json
assets/trajectory-app/data/BACKGROUND.md
assets/trajectory-app/data/INFERENCE.md
```

Before upgrading, an Agent must:

1. Detect whether the target already exists.
2. Copy the three data files to a private temporary backup outside the repository.
3. Update or replace the Skill files.
4. Restore the user's three data files byte for byte.
5. Verify that `places.json` remains valid JSON and that its record count and a content hash match the backup.
6. Re-run the retrieval smoke test and frontend build.
7. Remove the temporary backup only after successful verification.

Do not use a destructive Git reset on an installation containing personal data. Do not commit, upload, print, summarize, or transmit the private files during deployment.

## ZIP deployment

A GitHub-ready archive is stored in [`releases/`](releases/). An Agent deploying from the ZIP should:

1. Verify that the archive has a single `external-self/` root directory.
2. Extract it under `<CODEX_HOME>/skills/`.
3. Preserve existing private data using the upgrade procedure above.
4. Confirm that `<CODEX_HOME>/skills/external-self/SKILL.md` exists.
5. Run the retrieval and frontend build checks.

The release archive intentionally excludes `node_modules`, Python caches, machine-specific paths, and real personal trajectory records.

## Run the trajectory map

From the installed Skill:

```powershell
cd assets/trajectory-app
npm ci
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173/`. The local Vite middleware reads and writes `assets/trajectory-app/data/places.json` through `GET /api/places` and `PUT /api/places`.

The retrieval and research workflow is read-only. It must never call the write endpoint or modify FACT data. Writes are allowed only when the user explicitly edits nodes through the map application or explicitly requests a data mutation.

### Automatic first-use onboarding

When the selected `places.json` is empty, the Skill uses the map as the required collection surface instead of interviewing the user in chat. The deterministic helper starts or reuses the local web app and returns its verified URL:

```powershell
python scripts/ensure_trajectory_map.py --data assets/trajectory-app/data/places.json
```

The helper can serve a separate active project's FACT file through the bundled UI. It passes that absolute path to Vite with `TRAJECTORY_DATA_FILE`, chooses a free local port when `5173` is unavailable, waits for the API to respond, and records per-data-source runtime state in the operating system's temporary directory.

The Agent should present the returned URL as a clickable link and tell the user to click the map, complete the five descriptive fields, and save. After the user confirms completion, the Agent reruns retrieval against the same file and resumes the original task.

## Personal data model

The three context classes are separate provenance domains:

- **FACT JSON**: user-entered trajectory nodes in `places.json`.
- **BACKGROUND MD**: later user-provided context about a life stage.
- **INFERENCE MD**: AI-derived relationships and hypotheses.

Content must not migrate between these classes. External search results are temporary evidence and must not be persisted into FACT.

The public `places.json` starts as an empty array so first use enters map onboarding. User-created nodes remain private to the local installation. Each node follows this shape:

```json
{
  "id": 1000000000001,
  "name": "地点名称",
  "city": "城市",
  "timePoint": "2020-01-01",
  "durationYears": 1,
  "event": "事件详情上下文",
  "longitude": 121.4737,
  "latitude": 31.2304
}
```

## Visual evidence behavior

When reliable media exists, the Skill directs the host to display verified images and videos next to the discovery they support. Historical responses aim for approximately 2-4 strong visual artifacts overall.

Every displayed artifact should identify its date, source or channel, provenance, and relationship to the finding. Decorative stock images, modern replacements, undated reposts, and misattributed media are rejected. When visuals cannot be verified, the Skill uses textual evidence instead of padding the response.

## Repository layout

```text
external-self/
|-- SKILL.md
|-- README.md
|-- LICENSE
|-- references/
|-- scripts/retrieve_context.py
|-- evals/evals.json
|-- releases/
`-- assets/trajectory-app/
    |-- data/
    |-- src/
    |-- public/
    |-- dist/
    |-- package.json
    `-- vite.config.ts
```

## Validation

The Skill can be validated with Codex's `skill-creator` validator when available:

```powershell
$env:PYTHONUTF8 = '1'
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

The `PYTHONUTF8` setting avoids locale-dependent decoding problems on Windows systems whose default Python encoding is not UTF-8.

## License

Released under the [MIT License](LICENSE).
