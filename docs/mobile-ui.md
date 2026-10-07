# Mobil visning (smartphones)

Webstedet er stadig **laptop-først** (vandret layout). Mobilvisningen er et rent
tillæg: ét medie-scopet regelsæt, der kun gælder under 760 px og forenkler til
lodret visning. Desktop er uændret.

| Fil | Rolle |
|---|---|
| `mockup/css/mobile.css` | `@media (max-width: 760px)`-regler: kompakt header, filtre bag en knap, tabeller som kort, stablede detaljesider, sidemenu som liste, landingsside i én kolonne. Linkes **sidst** i `<head>` på alle sider (også de genererede dagbogssider via `build_diary_pages.py`). |
| `mockup/js/active-filters.js` | Aktive-filter-chips (× fjerner ét filter, «Ryd alle») + tæller på «Filtrér». Alle bredder. Slå fra med `data-active-filters="off"` på `.facet-panel` (bruges på `diaries*.html`, hvis facetter er statiske). |
| `mockup/js/mobile-nav.js` | Åbn/luk filterpanelet på telefon + «Vis N resultater»-knap. |
| `mockup/js/table-view.js` | Giver hver `<td>` `data-label`, så rækker kan blive til kort på telefon. |

Begge scripts indlæses fra `js/nav.js` på sider med et `.facet-panel`.

## Regler

- Tilføj **aldrig** `overflow` til `.facet-panel` eller andre `position: sticky`-elementer med
  en `position: fixed`-efterkommer (iOS Safari-faldgruben i `CLAUDE.md`). På telefon er
  panelet `position: static`.
- Tap-mål ≥ 44 px, inputfelter 16 px (ellers zoomer iOS ind).
- Chips er kun en visning over de rigtige kontroller: fjernelse fjerner afkrydsningen / tømmer
  feltet og udløser samme `change`/`input`-hændelse, så FacetEngine og sidens egen
  bogstavlinje reagerer som ved et direkte klik.
- Test: Playwright med `isMobile`, viewport 360 og 390 px; ingen vandret scroll
  (slå `overflow-x: clip` fra under test, så den ikke skjuler fejl).
