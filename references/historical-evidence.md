# Historical Evidence Retrieval

## Purpose

Find concrete traces that genuinely existed around the user's time and place. Reconstruct texture, not a textbook timeline.

Prefer contemporaneous artifacts over retrospective summaries. Prefer ordinary, specific artifacts over globally famous events. Ask: “Would this have been visible, hearable, purchasable, discussed, or physically present around this person's life then?”

## Build the search frame

From one or more selected nodes, derive:

- Place at useful scales: neighborhood, district, city, school, mall, transit line, venue.
- Time window: exact date when available, otherwise year plus a narrow adjacent window.
- Life stage and environment: childhood, school, university, workplace, commuting, home life.
- Artifact classes likely to preserve lived texture.

Good artifact classes include:

- Original local news pages, portal pages, newspaper scans, and magazine issues.
- School, campus, shopping, transit, neighborhood, brand, and event pages.
- Contemporary blogs, forums, photo albums, advertisements, posters, television clips, and music videos.
- Buildings, shops, roads, routes, products, and institutions demonstrably present then.
- Archived pages or captures with a traceable original URL and capture date.

Avoid starting with broad queries such as “2007 中国大事” or “武汉历史”. Start with combinations such as year + district + artifact class, institution + year, transit route + year, school + event, or publication + issue date.

## Two-round workflow

### Round 1: candidate discovery

Run a compact, diverse query set. Seek 5–10 candidates across different artifact classes rather than many copies of the same summary.

For every candidate, record privately:

- Claimed publication date.
- Claimed event or creation date.
- Place.
- Source identity.
- Artifact type.
- Whether it appears contemporaneous or retrospective.
- What personal node makes it relevant.

### Round 2: verification and media

Verify the strongest candidates using the original page, archive metadata, publication issue information, official records, or a second independent source.

For images and media, verify that the media itself belongs to the claimed date and event. A modern article containing an old-looking image is not enough. Look for captions, upload/publication dates, issue numbers, archive records, or matching contemporaneous text.

Actively seek displayable visual evidence during this round instead of treating it as optional decoration. For a response containing two or three discoveries, aim to verify 2–4 images or videos overall. Prefer at least one visual for every major discovery, but omit visuals rather than weaken provenance.

For each media candidate, record privately:

- Direct media identity: what exactly the image, cover, poster, or footage depicts.
- Media creation, publication, broadcast, or upload date; distinguish these when they differ.
- Original publisher, publication, archive, institution, uploader, or channel.
- Location and event association.
- Whether the displayed file is original, an authenticated scan/capture, or a later repost.
- A stable page or media URL suitable for the host's native image/video presentation.

Search-result thumbnails are discovery leads, not evidence. Trace them to the original or a credible archive before displaying them.

## Source priority

Prefer, in order:

1. Original contemporaneous page or scan.
2. Archived copy of an original contemporaneous page.
3. Contemporary official or institutional record.
4. Contemporary blog, forum, or personal media with identifiable date and location.
5. Later secondary source that clearly cites the original artifact.
6. Retrospective overview, Wikipedia, repost, or undated image only as orientation.

A page written in 2025 about a 2007 event is a secondary source. Do not describe it as a 2007 artifact.

## Quality gate

Score each candidate before presenting it:

| Dimension | Score |
|---|---:|
| Contemporaneity is verified | 0–3 |
| Location relevance is specific | 0–3 |
| Source identity and reliability are clear | 0–3 |
| Non-genericity / ordinary concreteness | 0–3 |
| Media date and identity are verified | 0–2 |
| Personal relevance to selected node | 0–3 |

Normally present candidates scoring at least 10, with at least 2 in contemporaneity, source identity, and personal relevance. A famous event receives no automatic bonus. A mundane magazine cover can outrank it when the cover is more specific, contemporary, and evocative.

A visual must score 2 for media date and identity before it is used as evidence. If the underlying discovery passes but its visual does not, present the discovery in text and state that a reliable image or video could not be verified.

## Output

Present one to three strong discoveries rather than a long list. For each:

- Anchor it to the user's node.
- Describe the artifact concretely.
- State publication date separately from event date when they differ.
- Say whether it is primary contemporaneous evidence or a secondary source.
- Explain briefly why it evokes that time and place.
- Cite the source in the host environment's native form.

Immediately after or within each discovery, display the verified image or video using the host's native Markdown/media syntax. Add a concise caption containing:

- What is shown.
- Media date and, if different, event date.
- Original source, publisher, archive, uploader, or channel.
- Whether it is contemporaneous primary evidence, an authenticated archival copy, or a later secondary presentation.

For video, prefer an inline player. If the host cannot play it inline, use a verified clickable thumbnail/preview and title rather than a bare URL. Never substitute an unrelated modern image simply because it embeds more easily.

If the date, location, or media identity remains uncertain, say so or omit the candidate.
