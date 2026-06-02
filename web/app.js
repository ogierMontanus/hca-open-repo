const DATA = "data/";

const state = {
  places: [],
  visits: {},
  timeline: {},
  works: {},
  filter: "",
  selectedId: null,
};

async function loadAll() {
  const [manifest, places, visits, timeline, works] = await Promise.all([
    fetch(DATA + "manifest.json").then(r => r.json()),
    fetch(DATA + "places.json").then(r => r.json()),
    fetch(DATA + "places_visits.json").then(r => r.json()),
    fetch(DATA + "places_timeline.json").then(r => r.json()),
    fetch(DATA + "places_works.json").then(r => r.json()),
  ]);
  state.places = places;
  state.visits = visits;
  state.timeline = timeline;
  state.works = works;
  renderManifest(manifest);
  renderList();
}

function renderManifest(m) {
  const c = m.counts || {};
  document.getElementById("manifest-line").textContent =
    `Built ${m.built_at} from ${m.source_xlsx ?? "—"} · ` +
    `${c.places ?? 0} places · ${c.place_references ?? 0} place-references · ` +
    `${c.diary_entries ?? 0} diary entries`;
}

function renderList() {
  const ol = document.getElementById("place-list");
  const q = state.filter.toLowerCase();
  const ranked = state.places
    .filter(p => !q || p.label.toLowerCase().includes(q))
    .sort((a, b) => b.visit_count - a.visit_count || a.label.localeCompare(b.label))
    .slice(0, 300);
  ol.innerHTML = "";
  for (const p of ranked) {
    const li = document.createElement("li");
    li.dataset.id = p.id;
    li.innerHTML =
      `<span class="label">${escape(p.label)}</span>` +
      `<span class="count">${p.visit_count}</span>`;
    if (p.id === state.selectedId) li.classList.add("selected");
    li.addEventListener("click", () => selectPlace(p.id));
    ol.appendChild(li);
  }
}

function selectPlace(id) {
  state.selectedId = id;
  const place = state.places.find(p => p.id === id);
  if (!place) return;

  document.getElementById("detail-empty").hidden = true;
  document.getElementById("detail").hidden = false;
  document.getElementById("detail-label").textContent = place.label;
  document.getElementById("detail-meta").textContent =
    `${place.visit_count} diary reference${place.visit_count === 1 ? "" : "s"}`;

  renderMap(place);
  renderTimeline(id);
  renderWorks(id);
  renderVisits(id);
  renderList();
}

let leafletMap = null;
function renderMap(place) {
  if (!leafletMap) {
    leafletMap = L.map("map").setView([55.6, 12.6], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 18,
    }).addTo(leafletMap);
  }
  leafletMap.eachLayer(l => { if (l instanceof L.Marker) leafletMap.removeLayer(l); });
  if (place.lat != null && place.lon != null) {
    L.marker([place.lat, place.lon]).addTo(leafletMap).bindPopup(place.label).openPopup();
    leafletMap.setView([place.lat, place.lon], 6);
  }
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

loadAll().catch(err => {
  document.getElementById("manifest-line").textContent =
    `Failed to load data: ${err.message}`;
});
