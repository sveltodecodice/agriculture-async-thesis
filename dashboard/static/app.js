const store = {
  snapshot: null,
  crops: [],
  revision: -1,
  pollIntervalMs: 2000,
  viewKey: '',
  ui: {
    operationTab: {},
    showAllSeeds: {},
    selectedSeed: {},
  },
};

const page = document.getElementById('page');
const sidebar = document.getElementById('sidebar');
const backdrop = document.getElementById('backdrop');
const toastEl = document.getElementById('toast');

const esc = (v) => String(v ?? '—').replace(/[&<>'"]/g, c => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;',
}[c]));
const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const value = (v, unit = '', digits = 1) => {
  const n = num(v);
  return n === null ? '—' : `${n.toFixed(digits)}${unit}`;
};
const percent = (v, digits = 0) => {
  const n = num(v);
  if (n === null) return '—';
  return `${(Math.abs(n) <= 1 ? n * 100 : n).toFixed(digits)}%`;
};
const percentNumber = (v) => {
  const n = num(v);
  if (n === null) return null;
  return Math.abs(n) <= 1 ? n * 100 : n;
};
const clamp = (v, min, max) => Math.max(min, Math.min(max, Number(v) || 0));
const normalize = (v) => String(v || '').trim().toLowerCase().replaceAll('_', '-').replaceAll(' ', '-');

const campLabel = (id) => /^field_([a-z])$/i.test(id || '')
  ? `Campo ${id.slice(-1).toUpperCase()}`
  : String(id || '').replaceAll('_', ' ');

const seasonLabel = (v) => ({
  winter:'Inverno', spring:'Primavera', summer:'Estate',
  autumn:'Autunno', fall:'Autunno',
})[String(v || '').toLowerCase()] || (v || '—');

const stageLabel = (v) => ({
  EMPTY:'Vuoto',
  PLANTED:'Seminato',
  GERMINATING:'Germinazione',
  GROWING:'Crescita',
  VEGETATIVE:'Fase vegetativa',
  FLOWERING:'Fioritura',
  FRUITING:'Fruttificazione',
  MATURING:'Maturazione',
  READY_FOR_HARVEST:'Pronto al raccolto',
})[String(v || '').toUpperCase()] || (v || '—');

const operationLabel = (v) => ({
  idle:'In attesa',
  irrigating:'Irrigazione in corso',
  reoxygenating:'Riossigenazione in corso',
  unknown:'Sconosciuta',
})[String(v || '').toLowerCase()] || (v || '—');

const actionLabel = (v) => ({
  irrigate:'Irrigazione',
  reoxygenate:'Riossigenazione',
  plant:'Semina',
  clear:'Svuotamento campo',
  restart:'Reimpostazione stato',
  skip:'Avanzamento simulazione',
})[String(v || '').toLowerCase()] || (v || '—');

const eventLabel = (v) => ({
  AUTO_PLANT:'Semina automatica',
  AUTO_IRRIGATE:'Irrigazione automatica',
  AUTO_HARVEST:'Raccolta automatica',
})[String(v || '').toUpperCase()] || 'Attività';

const healthLabel = (raw) => {
  const map = {
    HEALTHY:'Regolare',
    'FIELD IS EMPTY':'Campo vuoto',
    TOO_DRY:'Terreno troppo secco',
    TOO_WET:'Terreno troppo umido',
    TOO_COLD:'Temperatura troppo bassa',
    TOO_HOT:'Temperatura troppo alta',
    UNFAVORABLE_SEASON:'Stagione non favorevole',
    UNKNOWN:'Sconosciuto',
  };
  if (!raw) return '—';
  return String(raw).split(',').map(x => map[x.trim().toUpperCase()] || x.trim()).join(', ');
};

const weatherMap = {
  sun:['Soleggiato','☀'], sunny:['Soleggiato','☀'], clear:['Sereno','☀'],
  cloudy:['Nuvoloso','☁'], clouds:['Nuvoloso','☁'], overcast:['Coperto','☁'],
  rain:['Pioggia','☂'], rainy:['Pioggia','☂'], drizzle:['Pioviggine','☂'],
  storm:['Temporale','⚡'], thunderstorm:['Temporale','⚡'],
  fog:['Nebbia','≋'], mist:['Foschia','≋'], snow:['Neve','❄'], windy:['Ventoso','↝'],
};

function weatherInfo(v) {
  const hit = weatherMap[String(v || '').toLowerCase()];
  return hit ? { label: hit[0], icon: hit[1] } : {
    label: v ? String(v) : 'Dato non disponibile',
    icon: '○',
  };
}

function italianText(raw) {
  if (!raw) return '—';
  let text = String(raw);
  const replacements = [
    ['Weather:', 'Meteo:'],
    ['Moist:', 'Umidità:'],
    ['Oxy:', 'Ossigeno:'],
    ['Soil:', 'Terreno:'],
    ['Water:', 'Acqua:'],
    ['Pump:', 'Pompa:'],
    ['Plant:', 'Coltura:'],
    ['Stage:', 'Fase:'],
    ['Health:', 'Salute:'],
    ['Camp Manager', 'Gestore centrale'],
    ['Irrigator', 'Irrigatore'],
    ['Seeder', 'Seminatrice'],
    ['Harvester', 'Raccoglitore'],
    ['Ambient Sensor', 'Sensore ambientale'],
    ['Terrain Sensor', 'Sensore terreno'],
    ['Plantation Sensor', 'Sensore piantagione'],
    ['FIELD IS EMPTY', 'CAMPO VUOTO'],
    ['HEALTHY', 'REGOLARE'],
    ['TOO_DRY', 'TROPPO SECCO'],
    ['TOO_WET', 'TROPPO UMIDO'],
    ['TOO_COLD', 'TROPPO FREDDO'],
    ['TOO_HOT', 'TROPPO CALDO'],
    ['UNFAVORABLE_SEASON', 'STAGIONE NON FAVOREVOLE'],
    [' | Pump: ON', ' | Pompa: ATTIVA'],
    [' | Pump: OFF', ' | Pompa: FERMA'],
  ];
  for (const [from, to] of replacements) text = text.replaceAll(from, to);
  return text;
}

function camp(id) {
  return store.snapshot?.camps?.[id] || {};
}
function campIds() {
  return Object.keys(store.snapshot?.camps || {});
}
function farmDate() {
  for (const id of campIds()) {
    const date = camp(id).environment?.date;
    if (date) return date;
  }
  return '—';
}
function hasTelemetry(c) {
  const e = c.environment || {};
  const t = c.terrain || {};
  return [e.temperature, e.weather, e.date, t.soil_moisture, t.oxygenation, t.soil_type]
    .some(v => v !== null && v !== undefined);
}

function fieldState(c) {
  const p = c.plantation || {};
  const health = String(p.health || '').toUpperCase();
  const stage = String(p.growth_stage || '').toUpperCase();

  if (!hasTelemetry(c) && !p.last_status_at) {
    return { tone:'neutral', label:'Dati in attesa', description:'In attesa della prima telemetria dei sensori.' };
  }
  if (!p.occupied) {
    return { tone:'neutral', label:'Campo libero', description:'Nessuna coltura presente.' };
  }
  if (stage === 'READY_FOR_HARVEST') {
    return { tone:'warn', label:'Pronto al raccolto', description:'La coltura ha completato il ciclo di crescita.' };
  }
  if (health === 'HEALTHY') {
    return { tone:'good', label:'Regolare', description:'Parametri della coltura nei valori previsti.' };
  }
  if (health && health !== 'FIELD IS EMPTY' && health !== 'UNKNOWN') {
    return { tone:'warn', label:'Da monitorare', description:healthLabel(health) };
  }
  return { tone:'neutral', label:'In osservazione', description:'Stato disponibile ma non ancora classificato.' };
}

function suggested(c) {
  const policy = c.manager_policy || {};
  if (policy.harvest?.automatic_required) {
    return ['warn', 'Raccolta automatica', 'Il Gestore centrale richiederà la raccolta.'];
  }
  if (policy.irrigation?.automatic_required) {
    return ['warn', 'Irrigazione automatica',
      `Incremento previsto di circa ${value(policy.irrigation.needed_water_pct, '%', 1)}.`];
  }
  if (policy.oxygenation?.automatic_required) {
    return ['warn', 'Riossigenazione automatica', 'Ossigenazione sotto la soglia del 30%.'];
  }
  if (!c.plantation?.occupied) {
    return ['neutral', 'Semina automatica',
      'Il Gestore centrale sceglierà la coltura in base a stagione, terreno e umidità.'];
  }
  return ['good', 'Nessuna azione richiesta', 'Il Gestore centrale continua il monitoraggio.'];
}

const pill = (tone, label) => `<span class="pill ${tone}">${esc(label)}</span>`;
const metric = (label, val) =>
  `<div class="metric"><span>${esc(label)}</span><strong>${esc(val)}</strong></div>`;
const row = (label, val) =>
  `<div class="row"><span>${esc(label)}</span><strong>${esc(val)}</strong></div>`;

async function getJSON(url, options) {
  const response = await fetch(url, { cache:'no-store', ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Richiesta non riuscita (${response.status})`);
  return data;
}

async function sendCommand(id, action, params = {}) {
  return getJSON(`/api/camps/${id}/commands/${action}`, {
    method:'POST',
    headers:{ 'Content-Type':'application/json' },
    body:JSON.stringify(params),
  });
}

function toast(message, error = false) {
  toastEl.textContent = message;
  toastEl.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { toastEl.className = 'toast'; }, 2400);
}

function route() {
  const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'field' && parts[1]) return { page:'field', id:parts[1] };
  if (parts[0] === 'activity') return { page:'activity' };
  if (parts[0] === 'diagnostics') return { page:'diagnostics' };
  return { page:'home' };
}

function routeKey(r) {
  return r.page === 'field' ? `field:${r.id}` : r.page;
}

function go(path) {
  location.hash = path === 'home' ? '#/' : `#/${path}`;
}

function setHeader(kicker, title, tools = '') {
  document.getElementById('pageKicker').textContent = kicker;
  document.getElementById('pageTitle').textContent = title;
  document.getElementById('topbarTools').innerHTML = tools;
}

function setHTML(id, html) {
  const node = document.getElementById(id);
  if (node) node.innerHTML = html;
}

function renderSidebar() {
  const current = route();
  document.querySelectorAll('[data-route]').forEach(button => {
    button.classList.toggle('active', button.dataset.route === current.page);
  });

  const nav = document.getElementById('fieldNav');
  nav.innerHTML = campIds().map(id => {
    const c = camp(id);
    const state = fieldState(c);
    const active = current.page === 'field' && current.id === id;
    return `<button class="${active ? 'active' : ''}" data-field="${esc(id)}">
      <span>
        <strong>${esc(campLabel(id))}</strong>
        <small>${esc(c.plantation?.crop || 'Nessuna coltura')}</small>
      </span>
      <i class="dot ${state.tone}"></i>
    </button>`;
  }).join('');
}

/* ---------- PANORAMICA ---------- */

function homeSummaryHTML() {
  const rows = campIds().map(id => ({ id, c:camp(id), s:fieldState(camp(id)) }));
  const attention = rows.filter(x => ['warn','bad'].includes(x.s.tone)).length;
  const regular = rows.filter(x => x.s.tone === 'good').length;
  const free = rows.filter(x => !x.c.plantation?.occupied).length;
  const ready = rows.filter(x =>
    String(x.c.plantation?.growth_stage || '').toUpperCase() === 'READY_FOR_HARVEST'
  ).length;

  return `<article class="card dark summary">
    <div>
      <p class="kicker">Stato agronomico</p>
      <h2>${attention
        ? `${attention} ${attention === 1 ? 'campo richiede' : 'campi richiedono'} attenzione`
        : 'Situazione agronomica regolare'}</h2>
      <p class="copy">Sintesi delle colture e dei principali parametri osservati.</p>
    </div>
    <div class="summary-stats">
      <div class="summary-stat"><span>Regolari</span><strong>${regular}</strong></div>
      <div class="summary-stat"><span>Da monitorare</span><strong>${attention}</strong></div>
      <div class="summary-stat"><span>Pronti al raccolto</span><strong>${ready}</strong></div>
      <div class="summary-stat"><span>Campi liberi</span><strong>${free}</strong></div>
    </div>
    <div class="field-strip">
      ${rows.map(x => `<div class="field-strip-item">
        <div>
          <small>${esc(campLabel(x.id))}</small>
          <strong>${esc(x.c.plantation?.crop || 'Nessuna coltura')}</strong>
        </div>
        ${pill(x.s.tone, x.s.label)}
      </div>`).join('')}
    </div>
  </article>`;
}

function weatherCard(id, environment) {
  const weather = weatherInfo(environment.weather);
  return `<article class="weather-field">
    <header class="weather-field-head">
      <div class="weather-field-title">
        <span>${esc(campLabel(id))}</span>
        <strong>${esc(weather.label)}</strong>
      </div>
      <div class="weather-field-icon" aria-hidden="true">${weather.icon}</div>
    </header>

    <div class="weather-primary">
      <strong>${value(environment.temperature, ' °C', 1)}</strong>
      <span>${esc(seasonLabel(environment.season))}</span>
    </div>

    <dl class="weather-data">
      <div><dt>Umidità aria</dt><dd>${value(environment.humidity_air, '%', 0)}</dd></div>
      <div><dt>Pioggia</dt><dd>${value(environment.rain_mm, ' mm', 1)}</dd></div>
      <div><dt>Vento</dt><dd>${value(environment.wind_kmh, ' km/h', 1)}</dd></div>
      <div><dt>Radiazione</dt><dd>${value(environment.radiation_wm2, ' W/m²', 0)}</dd></div>
    </dl>
  </article>`;
}

function homeWeatherHTML() {
  const ids = campIds();
  const environments = ids.map(id => camp(id).environment || {});
  const conditions = environments.map(e => String(e.weather || '')).filter(Boolean);
  const counts = {};
  conditions.forEach(x => { counts[x] = (counts[x] || 0) + 1; });
  const prevalent = Object.entries(counts).sort((a,b) => b[1] - a[1])[0]?.[0];
  const weather = weatherInfo(prevalent);
  const season = environments.find(e => e.season)?.season;

  return `<article class="card">
    <div class="weather-head">
      <div>
        <p class="kicker">Condizioni ambientali</p>
        <h2>Meteo corrente</h2>
        <p class="copy">Rapporto della simulazione basato sui sensori ambientali dei campi.</p>
      </div>
      <div class="weather-icon">${weather.icon}</div>
    </div>
    <div class="overview">
      ${metric('Giorno simulato', farmDate())}
      ${metric('Stagione', seasonLabel(season))}
      ${metric('Condizione prevalente', weather.label)}
    </div>
    <div class="weather-fields">
      ${ids.map(id => weatherCard(id, camp(id).environment || {})).join('')}
    </div>
  </article>`;
}

function fieldCard(id) {
  const c = camp(id);
  const p = c.plantation || {};
  const t = c.terrain || {};
  const state = fieldState(c);
  const growth = clamp(p.growth_percentage, 0, 100);
  const policy = suggested(c);
  const harvestText = p.time_left == null ? 'Non disponibile' : `${p.time_left} giorni`;

  return `<article class="card field-card" data-field="${esc(id)}">
    <header class="field-card-head">
      <div>
        <p class="kicker">${esc(campLabel(id))}</p>
        <h3 class="crop-name">${esc(p.crop || 'Nessuna coltura')}</h3>
        <p class="field-subtitle">
          ${esc(t.soil_type || 'Terreno non disponibile')} · ${esc(stageLabel(p.growth_stage))}
        </p>
      </div>
      ${pill(state.tone, state.label)}
    </header>

    <div class="field-key-data">
      <div>
        <span>Umidità suolo</span>
        <strong>${percent(t.soil_moisture)}</strong>
      </div>
      <div>
        <span>Ossigenazione</span>
        <strong>${value(t.oxygenation, '%', 0)}</strong>
      </div>
      <div>
        <span>Tempo al raccolto</span>
        <strong>${esc(harvestText)}</strong>
      </div>
    </div>

    <section class="growth-block" aria-label="Avanzamento della coltura">
      <div class="growth-head">
        <div>
          <span>Avanzamento crescita</span>
          <small>${esc(stageLabel(p.growth_stage))}</small>
        </div>
        <strong>${growth.toFixed(0)}%</strong>
      </div>
      <div class="progress descriptive" role="progressbar"
        aria-valuemin="0" aria-valuemax="100" aria-valuenow="${growth.toFixed(0)}"
        aria-label="Crescita ${growth.toFixed(0)}%">
        <div style="width:${growth}%"></div>
      </div>
      <div class="growth-scale"><span>Semina</span><span>Maturazione</span></div>
    </section>

    <div class="policy-box">
      <span>Gestione automatica</span>
      <strong>${esc(policy[1])}</strong>
      <span>${esc(policy[2])}</span>
    </div>
  </article>`;
}

function homeFieldsHTML() {
  return `<div class="section-head">
    <div>
      <p class="kicker">Dati dei campi</p>
      <h2>Colture e condizioni del terreno</h2>
      <p>Confronto immediato tra crescita, terreno e gestione automatica.</p>
    </div>
  </div>
  <div class="grid three">${campIds().map(fieldCard).join('')}</div>`;
}

function mountHome() {
  setHeader('Azienda agricola', 'Panoramica azienda', `<span class="tool">${esc(farmDate())}</span>`);
  page.innerHTML = `<div class="stack">
    <section id="homeSummary"></section>
    <section id="homeWeather"></section>
    <section id="homeFields"></section>
  </div>`;
  updateHome();
}

function updateHome() {
  document.getElementById('topbarTools').innerHTML = `<span class="tool">${esc(farmDate())}</span>`;
  setHTML('homeSummary', homeSummaryHTML());
  setHTML('homeWeather', homeWeatherHTML());
  setHTML('homeFields', homeFieldsHTML());
}

/* ---------- CAMPO ---------- */

function fieldMainHTML(id) {
  const c = camp(id);
  const e = c.environment || {};
  const t = c.terrain || {};
  const p = c.plantation || {};
  const sys = c.system || {};
  const auto = sys.automation || {};
  const irr = sys.actuators?.irrigator || {};
  const policy = c.manager_policy || {};
  const state = fieldState(c);
  const growth = clamp(p.growth_percentage, 0, 100);
  const candidates = policy.seeding?.candidates || [];
  const irrigPending = !!auto.irrigation?.pending;
  const oxyPending = !!auto.reoxygenation?.pending;

  return `
    <article class="card">
      <div class="hero">
        <div>
          <p class="kicker">Coltura</p>
          <h2 class="hero-title">${esc(p.crop || 'Nessuna coltura')}</h2>
          <p class="copy">${esc(state.description)}</p>
        </div>
        ${pill(state.tone, state.label)}
      </div>
      <div class="hero-stats">
        ${metric('Fase', stageLabel(p.growth_stage))}
        ${metric('Crescita', `${growth.toFixed(0)}%`)}
        ${metric('Raccolto', p.time_left == null ? '—' : `${p.time_left} giorni`)}
        ${metric('Salute', healthLabel(p.health))}
      </div>
      <div class="progress"><div style="width:${growth}%"></div></div>
    </article>

    <article class="card">
      <p class="kicker">Telemetria</p>
      <h3>Terreno e ambiente</h3>
      <div class="telemetry">
        ${metric('Umidità suolo', percent(t.soil_moisture))}
        ${metric('Ossigenazione', value(t.oxygenation, '%', 0))}
        ${metric('Tipo terreno', t.soil_type || '—')}
        ${metric('Temperatura', value(e.temperature, ' °C', 1))}
        ${metric('Umidità aria', value(e.humidity_air, '%', 0))}
        ${metric('Pioggia', value(e.rain_mm, ' mm', 1))}
        ${metric('Vento', value(e.wind_kmh, ' km/h', 1))}
        ${metric('Radiazione', value(e.radiation_wm2, ' W/m²', 0))}
      </div>
      ${!hasTelemetry(c)
        ? '<div class="empty">Telemetria non ancora ricevuta. I dati verranno aggiornati automaticamente.</div>'
        : ''}
    </article>

    <article class="card sand">
      <p class="kicker">Flusso irrigazione</p>
      <h3>Decisione → attuatore → conferma sensore</h3>
      <div class="rows">
        ${row('Richiesta irrigazione',
          irrigPending ? (auto.irrigation?.request_id || 'In attesa') : 'Nessuna')}
        ${row('Richiesta riossigenazione',
          oxyPending ? (auto.reoxygenation?.request_id || 'In attesa') : 'Nessuna')}
        ${row('Stato irrigatore', operationLabel(irr.operation))}
        ${row('Ultima irrigazione confermata', t.last_irrigation_id || '—')}
        ${row('Incremento ultima irrigazione', value(t.last_irrigation_amount_pct, '%', 1))}
        ${row('Ultima riossigenazione confermata', t.last_reoxygenation_id || '—')}
      </div>
    </article>

    <article class="card">
      <p class="kicker">Gestore centrale</p>
      <h3>Regole automatiche</h3>
      <div class="rows">
        ${row('Irrigazione',
          `${value(policy.irrigation?.target_min_pct, '%', 0)} → ${value(policy.irrigation?.target_after_pct, '%', 0)}`)}
        ${row('Ossigenazione', 'Soglia 30%')}
        ${row('Raccolta', 'Automatica a maturazione')}
        ${row('Autosemina', 'Dopo 3 giorni di campo vuoto')}
      </div>
      <div class="subsection">
        <h4>Tre colture consigliate</h4>
        <div class="candidate-list">
          ${candidates.length ? candidates.map((x, i) => `
            <div class="candidate">
              <div>
                <strong>${i + 1}. ${esc(x.name)}</strong>
                <small>
                  ${x.season_match ? 'Stagione adatta' : 'Stagione non ideale'} ·
                  ${x.soil_match ? 'Terreno ideale' : `Terreno ideale: ${esc(x.ideal_soil)}`}
                </small>
              </div>
              <strong>Δ ${value(x.distance_from_current_pct, '%', 1)}</strong>
            </div>`).join('')
            : '<div class="empty">Dati insufficienti per elaborare un consiglio.</div>'}
        </div>
      </div>
    </article>`;
}

function operationTabsHTML(id) {
  const active = store.ui.operationTab[id] || 'irrigazione';
  const tabs = [
    ['irrigazione', 'Irrigazione'],
    ['semina', 'Semina'],
    ['simulazione', 'Simulazione'],
    ['manutenzione', 'Manutenzione'],
  ];
  return `<div class="operation-tabs" role="tablist" aria-label="Operazioni disponibili">
    ${tabs.map(([key, label]) => `<button
      type="button"
      class="${active === key ? 'active' : ''}"
      data-operation-tab="${key}"
      role="tab"
      aria-selected="${active === key ? 'true' : 'false'}"
    >${label}</button>`).join('')}
  </div>`;
}

function cropCompatibility(crop, c) {
  const e = c.environment || {};
  const t = c.terrain || {};
  const soilOk = normalize(crop.ideal_soil) === normalize(t.soil_type);
  const season = String(e.season || '').toLowerCase();
  const seasonOk = crop.seasons?.some(x => String(x).toLowerCase() === season) || false;

  const moisture = percentNumber(t.soil_moisture);
  const minMoist = percentNumber(crop.min_moisture);
  const maxMoist = percentNumber(crop.max_moisture);
  const moistureOk = moisture !== null && minMoist !== null && maxMoist !== null
    ? moisture >= minMoist && moisture <= maxMoist
    : false;

  const temperature = num(e.temperature);
  const minTemp = num(crop.min_temp);
  const maxTemp = num(crop.max_temp);
  const temperatureOk = temperature !== null && minTemp !== null && maxTemp !== null
    ? temperature >= minTemp && temperature <= maxTemp
    : false;

  return {
    soilOk,
    seasonOk,
    moistureOk,
    temperatureOk,
    ideal: soilOk && seasonOk,
    moisture,
    minMoist,
    maxMoist,
    temperature,
    minTemp,
    maxTemp,
  };
}

function seedCardsHTML(id) {
  const c = camp(id);
  const showAll = !!store.ui.showAllSeeds[id];
  const recommended = new Set((c.manager_policy?.seeding?.candidates || []).map(x => x.key));

  const crops = store.crops
    .map(crop => ({ crop, check:cropCompatibility(crop, c) }))
    .filter(x => showAll || x.check.ideal)
    .sort((a, b) =>
      Number(b.check.ideal) - Number(a.check.ideal)
      || Number(recommended.has(b.crop.key)) - Number(recommended.has(a.crop.key))
      || a.crop.name.localeCompare(b.crop.name, 'it')
    );

  if (!crops.length) {
    return `<div class="empty">
      Nessuna coltura è ideale contemporaneamente per stagione e terreno.
      Attiva “Mostra tutte le colture” per visualizzare le alternative.
    </div>`;
  }

  const selected = store.ui.selectedSeed[id];
  return `<div class="seed-grid">${crops.map(({ crop, check }) => {
    const isSelected = selected === crop.key;
    const idealClass = check.ideal ? 'ideal' : 'not-ideal';
    return `<button type="button"
      class="seed-card ${idealClass} ${isSelected ? 'selected' : ''}"
      data-seed="${esc(crop.key)}"
      aria-pressed="${isSelected ? 'true' : 'false'}">
      <div class="seed-title">
        <strong>${esc(crop.name)}</strong>
        ${check.ideal
          ? '<span class="compat good">Ideale</span>'
          : '<span class="compat warn">Non ideale</span>'}
      </div>
      <div class="seed-badges">
        <span class="${check.soilOk ? 'ok' : 'no'}">Terreno ${check.soilOk ? 'adatto' : 'non ideale'}</span>
        <span class="${check.seasonOk ? 'ok' : 'no'}">Stagione ${check.seasonOk ? 'adatta' : 'non ideale'}</span>
        <span class="${check.moistureOk ? 'ok' : 'note'}">Umidità ${check.moistureOk ? 'adatta' : 'da regolare'}</span>
        <span class="${check.temperatureOk ? 'ok' : 'note'}">Temperatura ${check.temperatureOk ? 'adatta' : 'non ottimale'}</span>
      </div>
      <small>
        Terreno ideale: ${esc(crop.ideal_soil)} ·
        Umidità ${value(check.minMoist, '%', 0)}–${value(check.maxMoist, '%', 0)} ·
        Temperatura ${value(check.minTemp, ' °C', 0)}–${value(check.maxTemp, ' °C', 0)}
      </small>
      ${recommended.has(crop.key) ? '<em>Consigliata dal Gestore centrale</em>' : ''}
    </button>`;
  }).join('')}</div>`;
}

function operationPanelHTML(id) {
  const c = camp(id);
  const sys = c.system || {};
  const auto = sys.automation || {};
  const irr = sys.actuators?.irrigator || {};
  const p = c.plantation || {};
  const tab = store.ui.operationTab[id] || 'irrigazione';
  const irrigPending = !!auto.irrigation?.pending;
  const oxyPending = !!auto.reoxygenation?.pending;

  if (tab === 'semina') {
    const showAll = !!store.ui.showAllSeeds[id];
    const selected = store.ui.selectedSeed[id];
    const selectedCrop = store.crops.find(crop => crop.key === selected);
    const selectedVisible = !!selectedCrop
      && (showAll || cropCompatibility(selectedCrop, c).ideal);
    return `<div class="operation-panel" data-panel="semina">
      <div class="operation-title">
        <div>
          <h4>Selezione coltura</h4>
          <p>Per impostazione predefinita sono mostrate solo le colture ideali per stagione e terreno.</p>
        </div>
        <label class="switch-row">
          <input type="checkbox" id="showAllSeeds" ${showAll ? 'checked' : ''}>
          <span>Mostra tutte le colture</span>
        </label>
      </div>
      ${seedCardsHTML(id)}
      <button class="btn operation-primary" data-command="plant"
        ${!selectedVisible || p.occupied ? 'disabled' : ''}>
        ${p.occupied
          ? 'Campo già occupato'
          : selectedVisible
            ? 'Semina la coltura selezionata'
            : 'Seleziona una coltura visibile'}
      </button>
    </div>`;
  }

  if (tab === 'simulazione') {
    return `<div class="operation-panel" data-panel="simulazione">
      <h4>Avanzamento temporale</h4>
      <p>Il tempo simulato è gestito dal sensore ambientale.</p>
      <label class="field-label" for="skipDays">Giorni da avanzare</label>
      <div class="input-row">
        <input id="skipDays" class="input" type="number" min="1" max="30" value="1">
        <button class="btn orange" data-command="skip">Avanza simulazione</button>
      </div>
    </div>`;
  }

  if (tab === 'manutenzione') {
    return `<div class="operation-panel" data-panel="manutenzione">
      <h4>Manutenzione del campo</h4>
      <p>Azioni amministrative da usare solo quando necessario.</p>
      <div class="actions">
        <button class="btn secondary" data-command="clear">Svuota campo</button>
        <button class="btn danger" data-command="restart">Reimposta stato</button>
      </div>
    </div>`;
  }

  return `<div class="operation-panel" data-panel="irrigazione">
    <h4>Irrigazione e ossigenazione</h4>
    <p>Le richieste passano dal Gestore centrale e vengono eseguite dall’irrigatore.</p>
    <div class="operation-status">
      ${row('Stato irrigatore', operationLabel(irr.operation))}
      ${row('Irrigazione pendente', irrigPending ? 'Sì' : 'No')}
      ${row('Riossigenazione pendente', oxyPending ? 'Sì' : 'No')}
    </div>
    <div class="actions">
      <button class="btn" data-command="irrigate" ${irrigPending ? 'disabled' : ''}>
        ${irrigPending ? 'Irrigazione in attesa' : 'Irriga ora'}
      </button>
      <button class="btn secondary" data-command="reoxygenate" ${oxyPending ? 'disabled' : ''}>
        ${oxyPending ? 'Riossigenazione in attesa' : 'Riossigena ora'}
      </button>
    </div>
  </div>`;
}

function mountField(id) {
  if (!store.snapshot?.camps?.[id]) {
    setHeader('Campo', 'Non disponibile');
    page.innerHTML = '<div class="card"><h2>Campo non disponibile</h2></div>';
    return;
  }

  store.ui.operationTab[id] ||= 'irrigazione';
  setHeader(campLabel(id), camp(id).plantation?.crop || 'Nessuna coltura');

  page.innerHTML = `<div class="detail">
    <div class="detail-main" id="fieldLive"></div>
    <aside class="detail-side">
      <article class="card sand operations-card">
        <p class="kicker">Operazioni</p>
        <h3>Azioni sul campo</h3>
        ${operationTabsHTML(id)}
        <div id="operationPanel"></div>
      </article>
    </aside>
  </div>`;

  updateField(id);
  renderOperationPanel(id);
}

function updateField(id) {
  const c = camp(id);
  const p = c.plantation || {};
  const e = c.environment || {};
  setHeader(campLabel(id), p.crop || 'Nessuna coltura',
    `<span class="tool">${esc(e.date || '—')}</span>`);
  setHTML('fieldLive', fieldMainHTML(id));
  updateOperationStatus(id);
}

function renderOperationPanel(id) {
  setHTML('operationPanel', operationPanelHTML(id));
  document.querySelectorAll('[data-operation-tab]').forEach(button => {
    const active = button.dataset.operationTab === (store.ui.operationTab[id] || 'irrigazione');
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', active ? 'true' : 'false');
  });
}

function updateOperationStatus(id) {
  const panel = document.getElementById('operationPanel');
  if (!panel) return;
  const activeElement = document.activeElement;
  const editing = activeElement && panel.contains(activeElement)
    && ['INPUT', 'SELECT', 'TEXTAREA'].includes(activeElement.tagName);

  // Non ricreare il pannello mentre l'operatore sta scrivendo o selezionando.
  if (!editing && (store.ui.operationTab[id] || 'irrigazione') === 'irrigazione') {
    panel.innerHTML = operationPanelHTML(id);
  }
}

/* ---------- ATTIVITÀ ---------- */

function activityHTML() {
  const notifications = [...(store.snapshot?.notifications || [])].reverse();
  const activities = [...(store.snapshot?.activity || [])].reverse();
  const commands = [...(store.snapshot?.commands || [])].reverse();

  return `<div class="stack">
    <div class="grid two">
      <article class="card">
        <p class="kicker">Decisioni</p>
        <h2>Notifiche del Gestore centrale</h2>
        <div class="list">
          ${notifications.length ? notifications.map(x => `<div class="list-item">
            <div class="meta">
              <span>${esc(x.camp_id ? campLabel(x.camp_id) : 'Azienda')}</span>
              <span>${esc(x.received_at || '')}</span>
            </div>
            <strong>${esc(italianText(x.message))}</strong>
          </div>`).join('') : '<div class="empty">Nessuna notifica disponibile.</div>'}
        </div>
      </article>

      <article class="card">
        <p class="kicker">Cronologia</p>
        <h2>Attività automatiche</h2>
        <div class="list">
          ${activities.length ? activities.map(x => `<div class="list-item">
            <div class="meta">
              <span>${esc(eventLabel(x.event))}</span>
              <span>${esc(x.date || '')}</span>
            </div>
            <span>${esc(italianText(x.details))}</span>
          </div>`).join('') : '<div class="empty">Nessuna attività registrata.</div>'}
        </div>
      </article>
    </div>

    <article class="card">
      <p class="kicker">Operatore</p>
      <h2>Comandi inviati</h2>
      <div class="list">
        ${commands.length ? commands.map(x => `<div class="list-item">
          <div class="meta">
            <span>${esc(campLabel(x.camp_id))} · ${esc(actionLabel(x.action))}</span>
            <span>${esc(x.requested_at || '')}</span>
          </div>
          <span>${x.status === 'published' ? 'Pubblicato' : 'Errore durante l’invio del comando'}</span>
        </div>`).join('') : '<div class="empty">Nessun comando inviato.</div>'}
      </div>
    </article>
  </div>`;
}

function mountActivity() {
  setHeader('Azienda agricola', 'Attività');
  page.innerHTML = '<div id="activityLive"></div>';
  updateActivity();
}
function updateActivity() {
  setHTML('activityLive', activityHTML());
}

/* ---------- DIAGNOSTICA ---------- */

function sensorHTML(label, state = {}) {
  const online = String(state.status || '').toUpperCase() === 'ONLINE';
  return `<div class="sensor">
    <div>
      <strong>${esc(label)}</strong>
      <small>${online ? 'Attivo' : 'Non disponibile'}${state.operation
        ? ` · ${esc(operationLabel(state.operation))}` : ''}</small>
    </div>
    <strong>${state.latency_ms == null ? '—' : `${Math.round(state.latency_ms)} ms`}</strong>
  </div>`;
}

function diagnosticCard(id) {
  const sys = camp(id).system || {};
  const sensors = sys.sensors || {};
  const irrigator = sys.actuators?.irrigator || {};
  const healthy = sys.overall_health === 'HEALTHY';

  return `<article class="card">
    <div class="section-head">
      <div>
        <p class="kicker">${esc(campLabel(id))}</p>
        <h3>${healthy ? 'Regolare' : 'Degradato'}</h3>
      </div>
    </div>
    <div class="sensor-list">
      ${sensorHTML('Sensore ambientale', sensors.environment)}
      ${sensorHTML('Sensore terreno', sensors.terrain)}
      ${sensorHTML('Sensore piantagione', sensors.plantation)}
      ${sensorHTML('Irrigatore', irrigator)}
    </div>
    <div class="subsection">
      ${row('Irrigazione pendente',
        sys.automation?.irrigation?.pending ? (sys.automation.irrigation.request_id || 'Sì') : 'No')}
      ${row('Riossigenazione pendente',
        sys.automation?.reoxygenation?.pending ? (sys.automation.reoxygenation.request_id || 'Sì') : 'No')}
    </div>
  </article>`;
}

function diagnosticsHTML() {
  const snap = store.snapshot || {};
  const mqtt = snap.mqtt || {};
  const manager = snap.camp_manager || {};
  const ids = campIds();
  const activeSensors = ids.reduce((sum, id) =>
    sum + Object.values(camp(id).system?.sensors || {}).filter(x => x.status === 'ONLINE').length, 0);
  const activeIrrigators = ids.filter(id =>
    String(camp(id).system?.actuators?.irrigator?.status).toUpperCase() === 'ONLINE').length;

  return `<div class="stack">
    <div class="diag-top">
      ${metric('Connessione MQTT', mqtt.connected ? 'Connessa' : 'Disconnessa')}
      ${metric('Gestore centrale', manager.connected ? 'Attivo' : 'Non disponibile')}
      ${metric('Sensori attivi', `${activeSensors}/${ids.length * 3}`)}
      ${metric('Irrigatori attivi', `${activeIrrigators}/${ids.length}`)}
    </div>

    <article class="card">
      <p class="kicker">Comunicazione MQTT</p>
      <h2>Connessione della dashboard</h2>
      <div class="rows">
        ${row('Server MQTT', `${mqtt.host || '—'}:${mqtt.port || '—'}`)}
        ${row('Identificativo connessione', mqtt.client_id || '—')}
        ${row('Messaggi ricevuti', mqtt.message_count ?? 0)}
        ${row('Ultimo argomento', mqtt.last_topic || '—')}
        ${row('Ultimo errore tecnico',
          mqtt.last_error ? 'Errore registrato — consulta i log del contenitore' : 'Nessuno')}
      </div>
    </article>

    <div class="diag-fields">${ids.map(diagnosticCard).join('')}</div>
  </div>`;
}

function mountDiagnostics() {
  setHeader('Sistema', 'Diagnostica');
  page.innerHTML = '<div id="diagnosticsLive"></div>';
  updateDiagnostics();
}
function updateDiagnostics() {
  setHTML('diagnosticsLive', diagnosticsHTML());
}

/* ---------- AGGIORNAMENTO INCREMENTALE ---------- */

function mountCurrentView() {
  const current = route();
  store.viewKey = routeKey(current);
  renderSidebar();

  if (current.page === 'field') mountField(current.id);
  else if (current.page === 'activity') mountActivity();
  else if (current.page === 'diagnostics') mountDiagnostics();
  else mountHome();
}

function updateCurrentView() {
  if (!store.snapshot) return;

  const current = route();
  const key = routeKey(current);
  if (key !== store.viewKey) {
    mountCurrentView();
    return;
  }

  renderSidebar();

  if (current.page === 'field') updateField(current.id);
  else if (current.page === 'activity') updateActivity();
  else if (current.page === 'diagnostics') updateDiagnostics();
  else updateHome();
}

async function refreshState() {
  try {
    const snapshot = await getJSON('/api/state');
    if (snapshot.revision === store.revision) return;
    store.snapshot = snapshot;
    store.revision = snapshot.revision;
    updateCurrentView();
  } catch (error) {
    console.error(error);
  }
}

async function poll() {
  while (true) {
    await refreshState();
    await new Promise(resolve => setTimeout(resolve, store.pollIntervalMs));
  }
}

async function handleCommand(id, action) {
  try {
    const params = {};

    if (action === 'skip') {
      params.days = Math.max(1, Math.min(30,
        Number(document.getElementById('skipDays')?.value || 1)));
    }

    if (action === 'plant') {
      const selected = store.ui.selectedSeed[id];
      if (!selected) {
        toast('Seleziona prima una coltura.', true);
        return;
      }
      params.crop_key = selected;
    }

    await sendCommand(id, action, params);
    toast(`${actionLabel(action)}: comando inviato`);

    // Aggiorna i dati senza ricostruire l'interfaccia operativa.
    await refreshState();
  } catch (error) {
    toast(error.message, true);
  }
}

function bindEvents() {
  document.addEventListener('click', async (event) => {
    const routeButton = event.target.closest('[data-route]');
    if (routeButton) {
      go(routeButton.dataset.route);
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
      return;
    }

    const fieldButton = event.target.closest('[data-field]');
    if (fieldButton) {
      go(`field/${fieldButton.dataset.field}`);
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
      return;
    }

    const tabButton = event.target.closest('[data-operation-tab]');
    if (tabButton) {
      const current = route();
      if (current.page !== 'field') return;
      store.ui.operationTab[current.id] = tabButton.dataset.operationTab;
      renderOperationPanel(current.id);
      return;
    }

    const seedButton = event.target.closest('[data-seed]');
    if (seedButton) {
      const current = route();
      if (current.page !== 'field') return;
      store.ui.selectedSeed[current.id] = seedButton.dataset.seed;
      renderOperationPanel(current.id);
      return;
    }

    const commandButton = event.target.closest('[data-command]');
    if (commandButton) {
      const current = route();
      if (current.page !== 'field') return;
      await handleCommand(current.id, commandButton.dataset.command);
    }
  });

  document.addEventListener('change', (event) => {
    if (event.target.id !== 'showAllSeeds') return;
    const current = route();
    if (current.page !== 'field') return;
    store.ui.showAllSeeds[current.id] = event.target.checked;
    renderOperationPanel(current.id);
  });

  document.getElementById('menuButton').addEventListener('click', () => {
    sidebar.classList.add('open');
    backdrop.classList.add('open');
  });
  backdrop.addEventListener('click', () => {
    sidebar.classList.remove('open');
    backdrop.classList.remove('open');
  });

  window.addEventListener('hashchange', mountCurrentView);
}

async function start() {
  bindEvents();
  try {
    const [snapshot, crops, dashboardConfig] = await Promise.all([
      getJSON('/api/state'),
      getJSON('/api/crops'),
      getJSON('/api/config'),
    ]);
    store.snapshot = snapshot;
    store.crops = crops.crops || [];
    store.pollIntervalMs = Math.max(250, Number(dashboardConfig.polling_interval_seconds || 2) * 1000);
    store.revision = snapshot.revision;
    mountCurrentView();
    poll();
  } catch (error) {
    page.innerHTML = `<div class="card">
      <h2>Pannello non disponibile</h2>
      <p class="copy">${esc(error.message)}</p>
    </div>`;
  }
}

start();
