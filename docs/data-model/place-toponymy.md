# Place toponymy — historical spellings and modern aliases

The place register inherits the orthography of the printed indexes Andersen and
his nineteenth-century editors used. Many of the canonical labels are now
either obsolete spellings, archaic exonyms, or Danish forms that have since
been replaced by modern abbreviations. A reader typing the contemporary form
must still find the entry, and the entry's own card must make the connection
visible so the historical form is not a dead end.

This is planned future work. The current `places.html` lists only the
register's canonical label; alternative forms are not yet searchable or
shown on the place card.

## Two distinct mismatches

The pattern shows up in two categories that the system should treat the same
way but expose with different labels.

### 1. Old Danish spelling → modern Danish spelling

The register preserves the spelling Andersen used. Modern Danish has settled
on different forms.

| Register label | Modern Danish form | Notes |
|---|---|---|
| Sverrig | Sverige | nineteenth-century Danish spelling of Sweden |
| Kjøbenhavn | København | pre-1948 orthography |
| Bayern *(Tysk)* | Bayern | unchanged — included as a counter-example |

### 2. Long Danish form → abbreviation or current short form

Where a place is now habitually known by a Danish abbreviation or a shorter
modern Danish name.

| Register label | Modern alternative | Notes |
|---|---|---|
| Amerika (de forenede Stater) | USA | Danish abbreviation for *Amerikas Forenede Stater* |
| Det osmanniske Rige | Tyrkiet | political-geography shift, treat as alias for search; canonical card retains the historical name |

## Schema sketch

Mirror the `alias` table from `wemi-and-relations.md`, but scoped to places:

```sql
CREATE TABLE place_alias (
    alias_label  TEXT NOT NULL,
    canonical_id TEXT NOT NULL REFERENCES place(place_id),
    alias_type   TEXT NOT NULL,    -- 'historical_spelling' | 'modern_abbreviation' |
                                   -- 'modern_name' | 'exonym' | 'translation'
    language     TEXT,             -- 'da' | 'en' | 'de' | …
    note         TEXT
);

CREATE INDEX idx_place_alias_label ON place_alias (alias_label);
```

`alias_type` is preserved so the UI can choose how to render the link:
"Moderne stavning: Sverige", "Dansk forkortelse: USA", "Eksonym: Konstantinopel
(nu Istanbul)".

## UI behaviour

1. **Search.** A query for `Sverige` or `USA` resolves to the same place card
   as `Sverrig` or `Amerika (de forenede Stater)`. The search index unions
   canonical labels and `place_alias.alias_label`.
2. **Card head.** The place card always leads with the canonical (register)
   label so the source is preserved. Modern forms appear in a secondary line:
   *Sverrig — moderne: Sverige*.
3. **Place-tag chips.** When a diary page or a work mentions the place,
   typing the chip uses the canonical label; hovering shows the modern form.
4. **No silent rename.** The register's label is never replaced by the modern
   form — it is annotated. This keeps the link to the source text legible.

## Data sources

Three lanes, in increasing order of effort and yield:

- **Editorial list (start here).** A small curated CSV (`data/curated/
  place_alias.csv`) — hand-authored entries for the ~50 highest-traffic
  places where the modern Danish form differs. Sverige, USA, Tyrkiet, Italien
  (vs *Italia*), Tyskland (vs *Tyskland og*), etc.
- **Wikidata `sameAs` / `also known as` (`P31`/`skos:altLabel`).** Once each
  place has a Wikidata Q-number (separate reconciliation pass), `altLabel`
  on the Wikidata item is a free source of validated alternative forms.
  Filter to `da` and `en` first.
- **Historical-spelling table.** Generic rules ("Kj…" → "K…", "Sverrig" →
  "Sverige", "-tz" → "-ts", etc.) are tempting but produce false positives;
  prefer the curated list and Wikidata routes.

## Out of scope here

- Reconciliation of `place_alias` against Wikidata Q-numbers — handled by
  the separate authority-reconciliation workstream.
- Historical-period scoping ("this place was called X between 1850 and 1878")
  — would require a temporal join on `place_alias`; deferred until the model
  earns it.
- Multilingual interface labels — covered by `docs/i18n-policy.md`.
