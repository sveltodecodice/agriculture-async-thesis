const CAMPS = ['campo_1', 'campo_2', 'campo_3'];
const CARD_TONES = ['tone-green', 'tone-sand', 'tone-orange'];
let snapshot = null;
let activeView = window.location.hash === '#/diagnostics' ? 'diagnostics' : 'home';

const $ = (id) => document.getElementById(id);
const safe = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n = (v) => (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) ? null : Number(v);
const pct = (fraction) => n(fraction) === null ? '—' : `${(Number(fraction) * 100).toFixed(1)}%`;
const wholePct = (value) => n(value) === null ? '—' : `${Math.round(Number(value))}%`;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const STAGE_LABELS = {
  EMPTY: 'Campo libero',
  SEED: 'Semina',
  GERMINATION: 'Germinazione',
  SEEDLING: 'Piantina',
  VEGETATIVE: 'Crescita vegetativa',
  FLOWERING: 'Fioritura',
  FRUITING: 'Fruttificazione',
  RIPENING: 'Maturazione',
  READY_FOR_HARVEST: 'Pronto al raccolto',
  MATURE: 'Pronto al raccolto',
};

const SENSOR_LABELS = {
  environment: { label: 'Environment', description: 'Meteo e condizioni ambientali', short: 'ENV' },
  terrain: { label: 'Terrain', description: 'Suolo, acqua e ossigenazione', short: 'TER' },
  plantation: { label: 'Plantation', description: 'Coltura, crescita e salute', short: 'PLT' },
};

function fieldData(campId) {
  const camp = snapshot?.camps?.[campId] || {};
  return {
    camp,
    env: camp.environment || {},
    terrain: camp.terrain || {},
    plant: camp.plantation || {},
    system: camp.system || {},
  };
}

function stageLabel(raw) {
  const key = String(raw || 'EMPTY').toUpperCase();
  return STAGE_LABELS[key] || key.replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase());
}

function healthInfo(data) {
  const health = String(data.plant.health || '').toUpperCase();
  const stage = String(data.plant.growth_stage || '').toUpperCase();
  const occupied = Boolean(data.plant.occupied);
  const moisture = n(data.terrain.soil_moisture);
  const minM = n(data.plant.min_moisture);
  const maxM = n(data.plant.max_moisture ?? (minM !== null ? minM + 0.05 : null));
  const oxygen = n(data.terrain.oxygenation);

  if (!occupied || health.includes('EMPTY')) {
    return { label: 'Campo libero', tone: 'neutral', sentence: 'Il campo è disponibile per una nuova coltura.' };
  }
  if (stage.includes('READY') || stage.includes('MATURE') || (n(data.plant.time_left) !== null && Number(data.plant.time_left) <= 0)) {
    return { label: 'Pronto al raccolto', tone: 'good', sentence: `${data.plant.crop || 'La coltura'} ha completato il ciclo di crescita ed è pronta per il raccolto.` };
  }
  if (minM !== null && moisture !== null && moisture < minM) {
    return { label: 'Suolo secco', tone: 'warn', sentence: `L'umidità del suolo è sotto il livello ideale. È consigliato controllare l'irrigazione.` };
  }
  if (maxM !== null && moisture !== null && moisture > maxM) {
    return { label: 'Suolo umido', tone: 'warn', sentence: `L'umidità del suolo è sopra il range ideale della coltura.` };
  }
  if (oxygen !== null && oxygen < 30) {
    return { label: 'Da riossigenare', tone: 'warn', sentence: `L'ossigenazione del suolo è bassa e richiede attenzione.` };
  }
  if (health.includes('HEALTHY') || health === 'OK') {
    return { label: 'In salute', tone: 'good', sentence: `${data.plant.crop || 'La coltura'} procede regolarmente. Le condizioni principali sono nella norma.` };
  }
  return { label: 'Da monitorare', tone: 'warn', sentence: `Il campo richiede una verifica delle condizioni correnti.` };
}

function currentFarmDate() {
  const dates = CAMPS.map(id => fieldData(id).env.date).filter(Boolean);
  if (!dates.length) return '—';
  const counts = dates.reduce((acc, date) => ((acc[date] = (acc[date] || 0) + 1), acc), {});
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}

function commonValue(key) {
  const values = CAMPS.map(id => fieldData(id).env[key]).filter(v => v !== null && v !== undefined && v !== '');
  if (!values.length) return '—';
  const counts = values.reduce((acc, value) => ((acc[value] = (acc[value] || 0) + 1), acc), {});
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}

function formatTimestamp(value, includeDate = false) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('it-IT', includeDate
    ? { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }
    : { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function humanAge(seconds) {
  const value = n(seconds);
  if (value === null) return 'Mai ricevuto';
  if (value < 1) return 'Adesso';
  if (value < 60) return `${value.toFixed(value < 10 ? 1 : 0)} s fa`;
  return `${Math.floor(value / 60)} min fa`;
}

function latencyText(value) {
  const latency = n(value);
  if (latency === null) return 'Latenza non disponibile';
  if (latency < 1) return '< 1 ms';
  return `${Math.round(latency)} ms`;
}

function sensorState(sensor) {
  const status = String(sensor?.status || 'UNKNOWN').toUpperCase();
  if (status === 'ONLINE') return { online: true, label: 'Online', tone: 'good' };
  if (status === 'OFFLINE') return { online: false, label: 'Offline', tone: 'danger' };
  return { online: false, label: 'In attesa', tone: 'neutral' };
}

function diagnosticFieldInfo(campId) {
  const data = fieldData(campId);
  const system = data.system || {};
  const sensors = system.sensors || {};
  const sensorList = ['environment', 'terrain', 'plantation'].map(name => ({ name, ...(sensors[name] || {}) }));
  const onlineCount = sensorList.filter(sensor => String(sensor.status || '').toUpperCase() === 'ONLINE').length;
  const health = String(system.overall_health || 'UNKNOWN').toUpperCase();
  return { data, system, sensorList, onlineCount, health };
}

function renderConnections() {
  const mqttOnline = Boolean(snapshot?.mqtt?.connected);
  const managerOnline = Boolean(snapshot?.camp_manager?.connected);

  [['mqttStatus', mqttOnline], ['managerStatus', managerOnline]].forEach(([id, online]) => {
    const el = $(id);
    el.classList.toggle('online', online);
    el.classList.toggle('offline', !online);
    el.querySelector('strong').textContent = online ? (id === 'managerStatus' ? 'Online' : 'Connesso') : 'Non disponibile';
  });
}

function renderFields() {
  const grid = $('fieldsGrid');
  grid.innerHTML = CAMPS.map((campId, index) => {
    const data = fieldData(campId);
    const health = healthInfo(data);
    const growth = clamp(n(data.plant.growth_percentage) ?? 0, 0, 100);
    const timeLeft = n(data.plant.time_left);
    const timeText = !data.plant.occupied ? '—' : (timeLeft === null ? '—' : timeLeft <= 0 ? 'Pronto' : `${Math.ceil(timeLeft)} g`);
    const chipClass = health.tone === 'warn' ? 'warn' : health.tone === 'danger' ? 'danger' : health.tone === 'neutral' ? 'neutral' : '';
    return `
      <article class="field-card ${CARD_TONES[index]}">
        <div class="field-plate"></div>
        <div class="field-content">
          <div class="field-top">
            <div>
              <p class="field-name">${safe(campId.replace('_', ' '))}</p>
              <h3 class="field-crop">${safe(data.plant.occupied ? data.plant.crop : 'Campo libero')}</h3>
            </div>
            <span class="status-chip ${chipClass}">${safe(health.label)}</span>
          </div>
          <p class="field-summary">${safe(health.sentence)}</p>
          <div class="field-progress-head">
            <span>${safe(stageLabel(data.plant.growth_stage))}</span>
            <strong>${wholePct(growth)}</strong>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${growth}%"></div></div>
          <div class="field-stats">
            <div class="field-stat"><span>Umidità suolo</span><strong>${pct(data.terrain.soil_moisture)}</strong></div>
            <div class="field-stat"><span>Ossigenazione</span><strong>${n(data.terrain.oxygenation) === null ? '—' : `${Number(data.terrain.oxygenation).toFixed(1)}%`}</strong></div>
            <div class="field-stat"><span>Raccolto</span><strong>${timeText}</strong></div>
          </div>
        </div>
      </article>
    `;
  }).join('');
}

function renderReview() {
  const infos = CAMPS.map(id => healthInfo(fieldData(id)));
  const active = CAMPS.filter(id => fieldData(id).plant.occupied).length;
  const ready = infos.filter(info => info.label === 'Pronto al raccolto').length;
  const attention = infos.filter(info => info.tone === 'warn' || info.tone === 'danger').length;

  $('activeFields').textContent = `${active}/${CAMPS.length}`;
  $('attentionFields').textContent = attention;
  $('readyFields').textContent = ready;

  if (attention === 0 && ready === 0) {
    $('reviewTitle').textContent = 'Tutti i campi sono stabili.';
    $('reviewCopy').textContent = 'Le colture attive procedono normalmente e non risultano interventi urgenti al momento.';
  } else if (attention === 0 && ready > 0) {
    $('reviewTitle').textContent = ready === 1 ? 'Una coltura è pronta al raccolto.' : `${ready} colture sono pronte al raccolto.`;
    $('reviewCopy').textContent = 'Gli altri campi risultano stabili. Controlla i campi pronti per pianificare il raccolto.';
  } else {
    $('reviewTitle').textContent = attention === 1 ? 'Un campo richiede attenzione.' : `${attention} campi richiedono attenzione.`;
    const attentionCamps = CAMPS.filter(id => {
      const info = healthInfo(fieldData(id));
      return info.tone === 'warn' || info.tone === 'danger';
    }).map(id => id.toUpperCase().replace('_', ' '));
    $('reviewCopy').textContent = `Controlla ${attentionCamps.join(', ')}. Gli altri campi non presentano criticità immediate.`;
  }
}

function latestDiagnosticUpdate() {
  const values = CAMPS.map(id => fieldData(id).system.updated_at).filter(Boolean);
  if (!values.length) return null;
  return values.sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];
}

function renderDiagnosticSummary() {
  const infos = CAMPS.map(diagnosticFieldInfo);
  const sensorsOnline = infos.reduce((sum, info) => sum + info.onlineCount, 0);
  const totalSensors = CAMPS.length * 3;
  const degradedFields = infos.filter(info => info.health === 'DEGRADED').length;
  const healthyFields = infos.filter(info => info.health === 'HEALTHY').length;
  const mqttOnline = Boolean(snapshot?.mqtt?.connected);
  const managerOnline = Boolean(snapshot?.camp_manager?.connected);

  $('diagnosticLastUpdate').textContent = formatTimestamp(latestDiagnosticUpdate(), true);
  $('diagnosticSummary').innerHTML = `
    <article class="diag-summary-card diag-green">
      <span>Camp Manager</span>
      <strong>${managerOnline ? 'Online' : 'Offline'}</strong>
      <small>${managerOnline ? 'Heartbeat ricevuto regolarmente' : 'Heartbeat non recente'}</small>
    </article>
    <article class="diag-summary-card diag-sand">
      <span>MQTT gateway</span>
      <strong>${mqttOnline ? 'Connesso' : 'Disconnesso'}</strong>
      <small>${safe(snapshot?.mqtt?.last_topic || 'Nessun topic ricevuto')}</small>
    </article>
    <article class="diag-summary-card diag-orange">
      <span>Sensori online</span>
      <strong>${sensorsOnline}/${totalSensors}</strong>
      <small>Environment · Terrain · Plantation</small>
    </article>
    <article class="diag-summary-card ${degradedFields ? 'diag-alert' : 'diag-green'}">
      <span>Campi</span>
      <strong>${degradedFields ? `${degradedFields} degradati` : `${healthyFields} sani`}</strong>
      <small>${degradedFields ? 'Controllare i sensori offline' : 'Nessuna anomalia sensori rilevata'}</small>
    </article>
  `;
}

function renderDiagnosticsFields() {
  const grid = $('diagnosticFieldsGrid');
  grid.innerHTML = CAMPS.map((campId, index) => {
    const info = diagnosticFieldInfo(campId);
    const healthKnown = info.health !== 'UNKNOWN';
    const healthClass = info.health === 'HEALTHY' ? 'good' : info.health === 'DEGRADED' ? 'danger' : 'neutral';
    const healthLabel = info.health === 'HEALTHY' ? 'Sistema sano' : info.health === 'DEGRADED' ? 'Sistema degradato' : 'In attesa dati';
    const mqttReported = info.system.mqtt_connected;

    const sensorRows = info.sensorList.map(sensor => {
      const meta = SENSOR_LABELS[sensor.name];
      const state = sensorState(sensor);
      return `
        <div class="sensor-row ${state.online ? 'online' : state.tone === 'danger' ? 'offline' : 'unknown'}">
          <div class="sensor-mark">${meta.short}</div>
          <div class="sensor-copy">
            <div class="sensor-title-row">
              <strong>${meta.label}</strong>
              <span class="sensor-chip ${state.tone}">${state.label}</span>
            </div>
            <p>${meta.description}</p>
          </div>
          <div class="sensor-metrics">
            <div><span>Ultimo dato</span><strong>${humanAge(sensor.last_seen_seconds_ago)}</strong></div>
            <div><span>Latenza</span><strong>${latencyText(sensor.latency_ms)}</strong></div>
          </div>
        </div>
      `;
    }).join('');

    return `
      <article class="diagnostic-field-card ${CARD_TONES[index]}">
        <div class="diagnostic-field-plate"></div>
        <div class="diagnostic-field-content">
          <div class="diagnostic-field-head">
            <div>
              <p class="field-name">${safe(campId.replace('_', ' '))}</p>
              <h3>${safe(info.data.plant.occupied ? info.data.plant.crop : 'Campo libero')}</h3>
            </div>
            <span class="status-chip ${healthClass === 'danger' ? 'danger' : healthClass === 'neutral' ? 'neutral' : ''}">${healthLabel}</span>
          </div>

          <div class="diagnostic-meta">
            <div>
              <span>Sensori online</span>
              <strong>${info.onlineCount}/3</strong>
            </div>
            <div>
              <span>MQTT visto dal manager</span>
              <strong>${mqttReported === true ? 'Connesso' : mqttReported === false ? 'Non connesso' : '—'}</strong>
            </div>
            <div>
              <span>Ultimo controllo</span>
              <strong>${formatTimestamp(info.system.updated_at)}</strong>
            </div>
          </div>

          <div class="sensor-list">
            ${sensorRows}
          </div>

          ${healthKnown && info.health === 'DEGRADED'
            ? '<div class="diagnostic-note alert">Uno o più sensori non hanno inviato telemetria negli ultimi 30 secondi.</div>'
            : healthKnown
              ? '<div class="diagnostic-note ok">Tutti i sensori del campo stanno comunicando regolarmente.</div>'
              : '<div class="diagnostic-note neutral">In attesa del primo report diagnostico dal Camp Manager.</div>'}
        </div>
      </article>
    `;
  }).join('');
}

function renderHeader() {
  $('currentDate').textContent = currentFarmDate();
  $('currentSeason').textContent = commonValue('season');
  $('currentWeather').textContent = commonValue('weather');
  $('lastUpdate').textContent = snapshot?.generated_at ? formatTimestamp(snapshot.generated_at) : '—';
}

function renderView() {
  const diagnostics = activeView === 'diagnostics';
  $('homeView').classList.toggle('hidden', diagnostics);
  $('diagnosticsView').classList.toggle('hidden', !diagnostics);
  $('diagnosticButton').classList.toggle('hidden', diagnostics);
  $('homeButton').classList.toggle('hidden', !diagnostics);
  $('pageKicker').textContent = diagnostics ? 'SMART FARM / DIAGNOSTICA' : 'SMART FARM';
  $('pageTitle').textContent = diagnostics ? 'System diagnostics' : 'Farm overview';
  $('pageSubtitle').textContent = diagnostics
    ? 'Connettività e salute dei sensori per ogni campo.'
    : 'Stato corrente dei campi e delle colture.';

  if (diagnostics) {
    renderDiagnosticSummary();
    renderDiagnosticsFields();
  } else {
    renderReview();
    renderFields();
  }
}

function render() {
  if (!snapshot) return;
  renderHeader();
  renderConnections();
  renderView();
}

function goTo(view) {
  activeView = view;
  window.location.hash = view === 'diagnostics' ? '#/diagnostics' : '#/';
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function bootstrap() {
  $('diagnosticButton').addEventListener('click', () => goTo('diagnostics'));
  $('homeButton').addEventListener('click', () => goTo('home'));
  window.addEventListener('hashchange', () => {
    activeView = window.location.hash === '#/diagnostics' ? 'diagnostics' : 'home';
    render();
  });

  try {
    const res = await fetch('/api/state');
    snapshot = await res.json();
    render();

    const events = new EventSource('/api/events');
    events.addEventListener('state', event => {
      snapshot = JSON.parse(event.data);
      render();
    });
  } catch (error) {
    console.error(error);
  }
}

bootstrap();
