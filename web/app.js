const DATA = "data/";

const state = {
  places: [],
  visits: {},
  timeline: {},
  works: {},
  rejser: { journeys: [], legs_by_place_id: {} },
  journeyById: {},
  filter: "",
  country: "",
  geocodedOnly: false,
  selectedId: null,
};

async function loadAll() {
  const [manifest, places, visits, timeline, works, rejser] = await Promise.all([
    fetch(DATA + "manifest.json").then(r => r.json()),
    fetch(DATA + "places.json").then(r => r.json()),
    fetch(DATA + "places_visits.json").then(r => r.json()),
    fetch(DATA + "places_timeline.json").then(r => r.json()),
    fetch(DATA + "places_works.json").then(r => r.json()),
    fetch(DATA + "rejser.json").then(r => r.json()),
  ]);
  state.places = places;
  state.visits = visits;
  state.timeline = timeline;
  state.works = works;
  state.rejser = rejser;
  state.journeyById = Object.fromEntries(rejser.journeys.map(j => [j.rejse_id, j]));
  renderManifest(manifest);
  populateCountryFilter(manifest.places_by_country || {});
  renderList();
}

function populateCountryFilter(byCountry) {
  const sel = document.getElementById("country-filter");
  for (const [name, n] of Object.entries(byCountry)) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = `${name} (${n})`;
    sel.appendChild(opt);
  }
}

function renderManifest(m) {
  const c = m.counts || {};
  document.getElementById("manifest-line").textContent =
    `Built ${m.built_at} · ${c.places ?? 0} places ` +
    `(${c.places_geocoded ?? 0} geocoded via hcax.dk Rejser) · ` +
    `${c.place_references ?? 0} diary references · ` +
    `${c.rejser_journeys ?? 0} journeys, ${c.rejser_legs ?? 0} legs`;
}

function renderList() {
  const ol = document.getElementById("place-list");
  const q = state.filter.toLowerCase();
  let ranked = state.places
    .filter(p => !q || p.label.toLowerCase().includes(q));
  if (state.country) ranked = ranked.filter(p => p.country_da === state.country);
  if (state.geocodedOnly || state.country) ranked = ranked.filter(p => p.geocoded);
  ranked = ranked
    .sort((a, b) => {
      if (a.geocoded !== b.geocoded) return a.geocoded ? -1 : 1;
      return b.visit_count - a.visit_count || a.label.localeCompare(b.label);
    })
    .slice(0, 400);
  ol.innerHTML = "";
  for (const p of ranked) {
    const li = document.createElement("li");
    li.dataset.id = p.id;
    if (p.geocoded) li.classList.add("geocoded");
    if (p.id === state.selectedId) li.classList.add("selected");
    const pin = p.geocoded ? `<span class="pin" aria-label="geocoded">●</span>` : "";
    const journey = p.geocoded && p.journey_count
      ? `<span class="journey-tag">${p.journey_count}j</span>` : "";
    li.innerHTML =
      `${pin}<span class="label">${escape(p.label)}</span>` +
      `${journey}<span class="count">${p.visit_count}</span>`;
    li.addEventListener("click", () => selectPlace(p.id));
    ol.appendChild(li);
  }
  document.getElementById("place-list").setAttribute(
    "data-shown", ranked.length
  );
}

function selectPlace(id) {
  state.selectedId = id;
  const place = state.places.find(p => p.id === id);
  if (!place) return;

  document.getElementById("detail-empty").hidden = true;
  document.getElementById("detail").hidden = false;
  document.getElementById("detail-label-text").textContent = place.label;
  const badge = document.getElementById("detail-badge");
  badge.hidden = !place.geocoded;

  const meta = [];
  meta.push(`${place.visit_count} diary reference${place.visit_count === 1 ? "" : "s"}`);
  if (place.geocoded) {
    if (place.destination_en && place.destination_en !== place.label) {
      meta.push(`a.k.a. ${place.destination_en}`);
    }
    if (place.country_da) {
      meta.push(`${place.country_da}${place.country_en && place.country_en !== place.country_da ? " / " + place.country_en : ""}`);
    }
    meta.push(`${place.lat.toFixed(4)}, ${place.lon.toFixed(4)}`);
  }
  document.getElementById("detail-meta").textContent = meta.join(" · ");

  renderMap(place);
  renderJourneys(id);
  renderTimeline(id);
  renderWorks(id);
  renderVisits(id);
  renderList();
}

let leafletMap = null;
let leafletMarker = null;
function renderMap(place) {
  const mapNote = document.getElementById("map-note");
  if (!leafletMap) {
    leafletMap = L.map("map").setView([54, 12], 3);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 18,
    }).addTo(leafletMap);
  }
  if (leafletMarker) { leafletMap.removeLayer(leafletMarker); leafletMarker = null; }
  if (place.geocoded && place.lat != null && place.lon != null) {
    leafletMarker = L.marker([place.lat, place.lon]).addTo(leafletMap)
      .bindPopup(`<b>${escape(place.label)}</b>` +
        (place.destination_en && place.destination_en !== place.label
          ? `<br>${escape(place.destination_en)}` : ""))
      .openPopup();
    leafletMap.setView([place.lat, place.lon], 6);
    mapNote.textContent = `Coordinates from hcax.dk Rejser add-on.`;
    mapNote.classList.remove("warn");
  } else {
    leafletMap.setView([54, 12], 3);
    mapNote.textContent = "Not geocoded — this place is not in the hcax.dk Rejser table.";
    mapNote.classList.add("warn");
  }
}

function renderJourneys(id) {
  const legs = state.rejser.legs_by_place_id[id] || [];
  const section = document.getElementById("journeys-section");
  const ol = document.getElementById("journeys-list");
  if (legs.length === 0) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  const byJourney = new Map();
  for (const leg of legs) {
    if (!byJourney.has(leg.rejse_id)) byJourney.set(leg.rejse_id, []);
    byJourney.get(leg.rejse_id).push(leg);
  }
  const items = [];
  const sorted = [...byJourney.entries()].sort(
    (a, b) => parseInt(a[0], 10) - parseInt(b[0], 10)
  );
  for (const [rejseId, journeyLegs] of sorted) {
    const j = state.journeyById[rejseId] || {};
    const legBullets = journeyLegs
      .map(l => {
        const dates = [l.arrival_date, l.departure_date].filter(Boolean).join(" → ") || "—";
        return `<li>${escape(l.destination_type)} · ${escape(dates)}` +
          (l.arrival_method ? ` · ${escape(l.arrival_method)}` : "") +
          `</li>`;
      })
      .join("");
    items.push(
      `<li class="journey">` +
      `<div class="journey-title">${escape(j.title || ("Rejse " + rejseId))}</div>` +
      (j.countries ? `<div class="journey-meta muted">${escape(j.countries)}</div>` : "") +
      (j.description ? `<div class="journey-desc">${escape(j.description)}</div>` : "") +
      `<ul class="leg-list">${legBullets}</ul>` +
      `</li>`
    );
  }
  ol.innerHTML = items.join("");
}

function renderTimeline(id) {
  const years = state.timeline[id] || {};
  const entries = Object.entries(years).map(([y, n]) => [parseInt(y, 10), n]);
  const div = document.getElementById("timeline");
  if (entries.length === 0) {
    div.innerHTML = `<p class="muted">No dated mentions.</p>`;
    return;
  }
  const max = Math.max(...entries.map(([, n]) => n));
  div.innerHTML = entries
    .map(([y, n]) =>
      `<div class="bar" title="${y}: ${n}">` +
      `<span class="fill" style="height:${(n / max) * 100}%"></span>` +
      `<span class="year">${y}</span>` +
      `</div>`
    )
    .join("");
}

function renderWorks(id) {
  const works = state.works[id] || [];
  const ol = document.getElementById("works-list");
  if (works.length === 0) {
    ol.innerHTML = `<li class="muted">No co-occurring works.</li>`;
    return;
  }
  ol.innerHTML = works
    .map(w =>
      `<li><span class="label">${escape(w.work_label)}</span>` +
      `<span class="count">${w.page_count}</span></li>`
    )
    .join("");
}

function renderVisits(id) {
  const visits = state.visits[id] || [];
  const ol = document.getElementById("visits-list");
  if (visits.length === 0) {
    ol.innerHTML = `<li class="muted">No diary entries.</li>`;
    return;
  }
  ol.innerHTML = visits
    .slice(0, 50)
    .map(v =>
      `<li>` +
      `<span class="visit-date">${escape(v.date || v.year || "—")}</span>` +
      `<span class="visit-ref">vol ${escape(v.vol)} p.${escape(v.page)}</span>` +
      `<p class="visit-snippet">${escape(v.snippet)}</p>` +
      `</li>`
    )
    .join("");
  if (visits.length > 50) {
    const more = document.createElement("li");
    more.className = "muted";
    more.textContent = `… and ${visits.length - 50} more.`;
    ol.appendChild(more);
  }
}

function escape(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

document.getElementById("search").addEventListener("input", e => {
  state.filter = e.target.value;
  renderList();
});
document.getElementById("geocoded-only").addEventListener("change", e => {
  state.geocodedOnly = e.target.checked;
  renderList();
});
document.getElementById("country-filter").addEventListener("change", e => {
  state.country = e.target.value;
  renderList();
});

loadAll().catch(err => {
  document.getElementById("manifest-line").textContent =
    `Failed to load data: ${err.message}`;
});
