---
name: external-self
description: Retrieve a user's read-only life-trajectory context and use it to investigate memories, past periods or places, contemporaneous traces, or evidence-backed unexpected connections in the present. Use when the user asks about their past, 回忆, 人生经历, 某个时期, 某个地方, 以前发生的事情, what life felt like then, help finding an old artifact, 帮我找一个过去的东西, reconstructing a memory, or asks for 巧合 and 有意思的关联 across life nodes and current interests, even without naming this skill. Do not use for generic history, map editing, ordinary conversation, or unrelated web research. Context retrieval does not automatically require web search; search only when historical evidence or contemporary serendipity is actually needed.
---

# External Self

Use a person's own time-place nodes as anchors for finding external evidence and connections the person did not necessarily think to ask about.

The goal is not to summarize a life map. It is to discover what the outside world can reliably add to a personal moment.

## Non-negotiable data boundary

Treat the three context classes as separate provenance domains:

- **FACT JSON**: user-entered trajectory nodes. This is the Personal Context Source of Truth.
- **BACKGROUND MD**: later-learned background about a life stage, with its own provenance.
- **INFERENCE MD**: relationships or hypotheses inferred from evidence.

For this skill, all three are read-only. Never modify, overwrite, normalize, enrich, or backfill the FACT JSON. Never call a write endpoint such as `PUT /api/places`. Never move content between FACT, BACKGROUND, and INFERENCE. In particular, never write an inferred person, relationship, place, date, or event into FACT.

External search results are temporary evidence for the current answer. They are not personal facts.

Read [references/schemas.md](references/schemas.md) before retrieving personal context.

## Bundled trajectory application

This Skill includes a complete local trajectory web application at `assets/trajectory-app/`. It contains the React map UI, MapLibre marker component, Vite local JSON API, dependency lockfile, static assets, and a bundled `data/places.json` snapshot.

Use the bundled application when the user asks to run, copy, install, or continue the trajectory product from the Skill package:

```text
cd <skill-directory>/assets/trajectory-app
npm ci
npm run dev
```

Do not edit the bundled FACT JSON while performing memory retrieval or external research. The map UI may write it only when the user explicitly edits nodes through the application or explicitly asks for a data mutation. The retrieval workflow remains read-only.

When the user has a separate active trajectory project, prefer that project's `data/places.json` by passing `--data <path>` instead of silently mixing it with the bundled snapshot.

## Decide whether this skill is needed

Use the skill when the current conversation meaningfully involves the user's own past, a life stage, a place they lived, a personal event, an old artifact, or a request for an evidence-backed connection across personal nodes and the present.

Do not activate retrieval merely because the user mentions a year, city, history, or memory in the abstract. Do not use it for map CRUD, generic local history, travel planning, or ordinary companionship.

Classify the current turn:

1. **No retrieval**: ordinary chat or no personal relevance. Respond normally and do not search.
2. **Personal context only**: the answer depends on the user's own nodes but not the external world. Retrieve relevant nodes; do not search the web.
3. **Historical Evidence Retrieval**: the user wants traces of what existed or happened around a past personal time and place.
4. **Contemporary Serendipity Retrieval**: the user wants an unexpected but factual present-day connection involving two or more context nodes, current interests, people, works, companies, or projects.
5. **Combined**: use historical evidence first, then test whether it creates a meaningful present-day connection.

## Retrieve only relevant personal context

Do not dump the whole JSON into context unless it has five or fewer records and the task genuinely requires timeline-wide comparison.

1. Distill the current conversation into a compact retrieval query containing relevant dates, places, life stages, people, events, organizations, works, and current interests.
2. Run the bundled read-only retriever:

   ```text
   python <skill-directory>/scripts/retrieve_context.py --query "<distilled query>" --mode auto --limit 5
   ```

3. Use `--mode relevant` for a focused memory or known period. Use `--mode diverse` for a broad serendipity request that needs 2–5 nodes across different periods or cities.
4. Inspect only the returned nodes. By default the script can use the bundled JSON. If a separate active project is in scope, locate its `data/places.json` read-only and rerun with `--data <path>`.
5. If BACKGROUND or INFERENCE sidecars exist, read only sections connected to the selected node IDs, dates, cities, or events. Keep their labels visible in reasoning.
6. If no node fits, say that the available personal context does not anchor the request well enough. Ask one narrow question only when it would materially change retrieval.

The script is a lexical and timeline filter, not an oracle. Apply judgment after retrieval.

When a current interest appears only in conversation and not in FACT, treat it as a current-conversation anchor, not as Personal Context and not as a fact to persist.

## Decide whether to search the external world

Search only when the answer requires evidence outside personal context.

- Do not search to repeat facts already present in the user's nodes.
- Do search when the user asks what the period felt like, asks to find a past object or trace, asks whether an external connection exists, or when a factual claim needs verification.
- Prefer the environment's existing web search and browser capabilities. Do not bind the workflow to a provider-specific result format.
- Preserve source identity, dates, and links/citations in the host environment's native format.

For Historical Evidence Retrieval, read and follow [references/historical-evidence.md](references/historical-evidence.md).

For Contemporary Serendipity Retrieval, read and follow [references/serendipity.md](references/serendipity.md).

## Keep search efficient

Aim to complete external retrieval in two search rounds when possible:

- **Round 1 — candidate discovery**: use a small, varied query set derived from the selected nodes. Find candidate artifacts or connection paths.
- **Round 2 — verification and media**: verify dates, locations, source identity, originality, and image/media provenance for the strongest candidates.

Do not interpret “two rounds” as two individual queries. Batch a few purposeful queries per round when the tool permits. Add a third round only when a promising result cannot otherwise be verified.

## Evidence discipline

Separate every claim internally as one of:

- **Personal fact**: directly present in FACT JSON.
- **Background**: present in BACKGROUND MD.
- **External fact**: supported by a cited external source.
- **Inference**: reasoned connection derived from facts and evidence.
- **Hypothesis**: plausible but not sufficiently verified.

Never present an inference or hypothesis as a personal fact. When sources conflict, say so. When an image's date or identity cannot be verified, do not use it as proof.

## Visual evidence first

When a historical or serendipity discovery has verifiable visual or audiovisual evidence, actively retrieve and **show it in the answer**. Do not stop at describing an image, naming a video, or leaving all media behind text-only citations.

- Use the host's native Markdown image, media embed, preview, thumbnail, or equivalent presentation syntax.
- Place each image or video beside the discovery it supports, not in a detached gallery or link dump.
- For a historical answer with multiple discoveries, aim for 2–4 strong visual artifacts overall and at least one verified visual for each major discovery when available.
- For video, show an inline player when supported. Otherwise show a verified thumbnail or preview with a clearly clickable title/link. State the title, publication or upload date, source/channel, and why the footage belongs to the claimed time or event.
- Prefer contemporaneous magazine covers, posters, advertisements, archival photographs, street scenes, news footage, music videos, and event recordings over decorative or generic imagery.
- Treat the media itself as evidence: verify its date, subject, location, source identity, original publisher/uploader, and relationship to the claim. A correctly dated webpage does not automatically authenticate every image embedded in it.
- Never use stock imagery, modern replacement photos, undated reposts, search-result thumbnails without provenance, or merely similar-looking scenes to create atmosphere.
- If no visual crosses the verification threshold, say briefly that no reliable visual was found and present the textual evidence without padding.

Media quantity is a target, not permission to lower the evidence standard. Verified relevance always wins over visual volume.

## Output experience

Lead with the discovery, not the search process. A natural opening is:

- “我找到一个挺有意思的东西。”
- “我发现了一个你可能没想到的连接。”
- “这次没有找到足够可靠、又确实有意思的关联。”

Then explain:

1. Which personal node or nodes make the discovery relevant.
2. What the external artifact or connection is.
3. Why it is contemporaneous or why the connection is real.
4. What is fact versus inference or hypothesis.
5. The small number of sources that carry the claim.

Where verified media exists, weave it into those points so the user experiences the artifact directly. Give each visual a short factual caption with its date, source identity, and evidence status; do not make the user open a source merely to learn what the media is.

Avoid narrating query counts or presenting a search-engine dump. Avoid “命中注定”, “宇宙安排”, or manufactured sentiment. Surprise should come from the evidence itself.

If no result crosses the quality threshold, report that plainly rather than padding the answer with generic history or weak coincidences.

## Safety and privacy

Use only personal data already placed in scope by the user. Do not search for private individuals in ways that would expose sensitive personal information, infer protected traits, or identify someone from sparse clues. Keep queries no more personally identifying than necessary. Prefer public artifacts and public organizational connections.
