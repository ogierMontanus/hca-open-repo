# Design-dropzone — HCA Dagbogsregister

Denne mappe indeholder kanoniske HTML-preview-filer for UI-komponenterne i
mockuppen. De er uploadet til projektet **"HCA Dagbogsregister"** på
`claude.ai/design`, hvor du kan redigere dem visuelt i browseren.

## Filer

| Fil | Komponent | Design-gruppe |
|-----|-----------|---------------|
| `chips.html` | Entity-chips og typeahead-pills | Chips & Tags |
| `result-card.html` | Dagbogs-resultatkort (grid, liste, kompakt, featured) | Cards |
| `facet-panel.html` | Venstre filterpanel med grupper og valg-tilstand | Facet Panel |
| `page-hero.html` | Sidehoved-banner (standard, lille, sektion-farve-varianter) | Page Hero |
| `info-block.html` | Sidebar-metadataboks med tabel og chips | Info Block |
| `entity-layout.html` | To-kolonne hoved/sidebar-layout på detaljeside | Entity Layout |

Hver fil er selvstændig (ingen eksterne afhængigheder) og bruger de samme
CSS-variabler og klasser som `mockup/css/style.css`.

---

## Workflow: fra redigering i Claude Design til repo

```
claude.ai/design
      │  rediger komponent i browseren
      │  download opdateret HTML
      ▼
[fil et vilkårligt sted på disk]
      │
      │  python -X utf8 scripts/design_sync/apply_component.py
      │                  sti\til\info-block.html --list-usages
      ▼
scripts/design_sync/apply_component.py
      │  unwrapper bundler-format → ren HTML
      │  differ CSS-variabler mod style.css
      │  differ markup mod baseline i design/
      │  lister berørte mockup-sider
      ▼
design/info-block.html  ← opdateret baseline (git diff viser ændringer)
mockup/css/style.css    ← patches med --apply (CSS-variabel-ændringer)
mockup/*.html           ← manuel propagering af markup-ændringer
```

### Trin for trin

1. Rediger en komponent på `claude.ai/design`
2. Download den opdaterede HTML (ankommer som bundler-wrapper)
3. Kør scriptet:
   ```
   python -X utf8 scripts/design_sync/apply_component.py DOWNLOADED_FILE.html
   ```
4. Tilføj `--list-usages` for at se hvilke mockup-sider der bruger komponentens klasser
5. Tilføj `--apply` for at skrive CSS-variabel-ændringer direkte til `style.css`
6. Gennemgå `git diff design/` for markup-ændringer
7. Propagér label- og markup-ændringer manuelt til de listede mockup-sider

---

## Quirks og kendte falske positiver

| Symptom | Årsag | Handling |
|---------|-------|----------|
| `--font-sans` vises som ændret | Komponent-CSS bruger kompakt fallback-liste | Ignorer — ændr kun hvis bevidst |
| `<tbody>` tilføjes i diff | DOMParser normaliserer HTML | Harmløs — ignorer |
| `<!-- @dsCard -->` mangler | Bundleren fjerner den | Forventet — intet at gøre |
| Klasse-diff viser mange "ændringer" | Kompakte multi-property CSS-linjer | Tjek `git diff mockup/css/style.css` i stedet |

---

## Upload nye komponenter til Claude Design

Kræver en Claude Code-session med DesignSync-adgang:

```
# 1. Skriv ny komponentfil til design/
# 2. I Claude Code-session:
DesignSync list_projects               # find projectId
DesignSync finalize_plan               # lås filsti
DesignSync write_files                 # upload
```

**Projekt-ID:** `782f6333-b090-40f0-a7cb-5dfae3ca588a`
