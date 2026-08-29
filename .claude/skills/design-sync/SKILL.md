---
name: design-sync
description: Apply an updated component downloaded from Claude Design (claude.ai/design, project "HCA Dagbogsregister") back into the repo, or upload new/updated components to that project. Use when the user drops a downloaded design-component file on disk, mentions Claude Design, DesignSync, or the design-editing loop, or asks to sync design/ components with mockup/css/style.css.
---

# Claude Design — komponent-dropzone og pipeline

## Konceptet

UI-komponenter vedligeholdes som rene HTML-preview-filer i `design/`.
De uploades til projektet **"HCA Dagbogsregister"** på `claude.ai/design`
via `DesignSync`-værktøjet. Brugeren kan redigere dem visuelt i browseren
og downloade opdaterede versioner. Den downloadede fil (pakket ind i en
bundler-wrapper) droppes et vilkårligt sted på disk, og pipeline-scriptet
udpakker og analyserer ændringerne.

## Projektstruktur

| Sti | Indhold |
|-----|---------|
| `design/` | Kanoniske, rene HTML-komponent-filer (commited, tracket) |
| `scripts/design_sync/apply_component.py` | Pipeline-script |

**Claude Design projekt-ID:** `782f6333-b090-40f0-a7cb-5dfae3ca588a`

Komponenter (6 stk., alle grupper i Design-panelet):

| Fil | Gruppe |
|-----|--------|
| `chips.html` | Chips & Tags |
| `result-card.html` | Cards |
| `facet-panel.html` | Facet Panel |
| `page-hero.html` | Page Hero |
| `info-block.html` | Info Block |
| `entity-layout.html` | Entity Layout |

## Design-redigerings-loop

1. Åbn `claude.ai/design` → HCA Dagbogsregister → rediger en komponent
2. Download den opdaterede HTML (filen ankommer pakket i bundler-wrapper)
3. Drop filen et vilkårligt sted på disk
4. Kør pipeline-scriptet (Windows PowerShell):
   ```
   python -X utf8 scripts/design_sync/apply_component.py sti\til\info-block.html --list-usages
   ```
5. Scriptet printer: CSS-variabel-ændringer, klasse-ændringer, markup-diff,
   berørte mockup-filer
6. Tilføj `--apply` for at skrive CSS-variabel-ændringer direkte til
   `mockup/css/style.css`
7. `git diff design/` viser det fulde markup-diff til manuel propagering
8. Propagér label/markup-ændringer til de berørte mockup-sider i hånden

## Hvad pipeline-scriptet gør

- **Unwrapper** Claude Design bundler-format → ren HTML
- **CSS-variabel-diff**: sammenligner `:root`-blokken med `style.css`
  og rapporterer ændrede værdier (kan patches med `--apply`)
- **Klasse-diff**: sammenligner komponent-klasseregler med `style.css`
  (falske positiver kan forekomme ved kompakte CSS-one-liners i komponenten
  — ignorer disse og validér mod `git diff style.css` i stedet)
- **Markup-diff**: unified diff af HTML-strukturen (ekskl. `<style>`-blokken)
  mod den committede baseline i `design/`
- **`--list-usages`**: lister mockup-sider der bruger komponentens CSS-klasser

## Kendte quirks

- `--font-sans` optræder som "ændret" fordi komponent-CSS bruger en kortere
  fallback-liste end `style.css`. Det er et skrive-artefakt, ikke en
  designbeslutning — ignorer det med mindre du bevidst forkorter font-stakken.
- DOMParser i browseren tilføjer `<tbody>` og kollapser whitespace — disse
  vises i markup-diff'en men er harmløse HTML-normaliseringer.
- `<!-- @dsCard group="…" -->` kommentaren fjernes af bundleren — det er
  forventet adfærd.

## Upload af nye/opdaterede komponenter til Claude Design

Kør i en Claude Code-session (kræver DesignSync-værktøj):

```
DesignSync list_projects               → find projectId
DesignSync finalize_plan + write_files → push opdaterede design/-filer
```
