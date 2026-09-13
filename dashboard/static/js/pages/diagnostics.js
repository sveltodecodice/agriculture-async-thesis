import { CAMPS, store } from '../store.js';
import { safe, valueWithUnit } from '../format.js';
import { statusPill } from '../components.js';

const sensorNames = { environment: 'Ambiente', terrain: 'Terreno', plantation: 'Piantagione' };

function sensorRow(name, info = {}) {
  const online = String(info.status || 'UNKNOWN').toUpperCase() === 'ONLINE';
  const age = info.last_seen_seconds_ago === null || info.last_seen_seconds_ago === undefined ? 'mai ricevuto' : `${info.last_seen_seconds_ago}s fa`;
  return `
    <div class="sensor-row ${online ? '' : 'offline'}">
      <div class="sensor-icon">${name.slice(0,3).toUpperCase()}</div>
      <div class="sensor-copy"><strong>${sensorNames[name]}</strong><span>${online ? 'Online' : 'Offline'} · ${age}</span></div>
      <div class="sensor-latency"><strong>${valueWithUnit(info.latency_ms, ' ms', 0)}</strong><span>latenza</span></div>
    </div>`;
}

function diagnosticCard(campId, index) {
  const camp = store.snapshot.camps[campId];
  const system = camp.system || {};
  const healthy = system.overall_health === 'HEALTHY';
  const tone = ['green','sand','orange'][index];
  return `
    <article class="card ${tone}">
      <div class="card-header">
        <div><p class="card-kicker">${campId.toUpperCase()}</p><h3>${healthy ? 'Sensori regolari' : 'Verifica richiesta'}</h3></div>
        ${statusPill(healthy ? 'good' : 'warn', healthy ? 'Healthy' : 'Degraded')}
      </div>
      <div class="sensor-grid">${['environment','terrain','plantation'].map((name) => sensorRow(name, system.sensors?.[name])).join('')}</div>
      <div class="system-row"><span>Ultimo report</span><strong>${safe(system.updated_at || '—')}</strong></div>
    </article>`;
}

export function renderDiagnostics(page) {
  page.className = 'page page-diagnostics';
  const mqtt = Boolean(store.snapshot.mqtt?.connected);
  const manager = Boolean(store.snapshot.camp_manager?.connected);
  let onlineSensors = 0;
  let degraded = 0;

  CAMPS.forEach((id) => {
    const system = store.snapshot.camps[id]?.system || {};
    if (system.overall_health !== 'HEALTHY') degraded += 1;
    Object.values(system.sensors || {}).forEach((sensor) => { if (sensor.status === 'ONLINE') onlineSensors += 1; });
  });

  document.getElementById('pageKicker').textContent = 'Sistema';
  document.getElementById('pageTitle').textContent = 'Diagnostica';
  document.getElementById('topbarTools').innerHTML = `
    ${statusPill(mqtt ? 'good':'bad', mqtt ? 'MQTT online':'MQTT offline')}
    ${statusPill(manager ? 'good':'bad', manager ? 'Manager online':'Manager offline')}`;

  page.innerHTML = `
    <div class="content-stack">
      <article class="card dark">
        <div class="card-header">
          <div>
            <p class="card-kicker">Stato sistema</p>
            <h2>Servizi e sensori</h2>
            <p class="body-copy">Una sola vista per capire se il problema riguarda il broker, il Camp Manager o un sensore di campo.</p>
          </div>
        </div>
        <div class="system-overview">
          <div class="kpi-card"><span class="kpi-label">MQTT</span><strong class="kpi-value textual">${mqtt ? 'Online':'Offline'}</strong></div>
          <div class="kpi-card"><span class="kpi-label">Camp Manager</span><strong class="kpi-value textual">${manager ? 'Online':'Offline'}</strong></div>
          <div class="kpi-card"><span class="kpi-label">Sensori online</span><strong class="kpi-value">${onlineSensors}/9</strong></div>
          <div class="kpi-card"><span class="kpi-label">Campi degradati</span><strong class="kpi-value">${degraded}</strong></div>
        </div>
      </article>

      <div class="section-heading">
        <div><h2>Diagnostica per campo</h2><p>Disponibilità, freschezza e latenza dei tre sensori monitorati dal Camp Manager.</p></div>
      </div>

      <section class="diagnostic-fields">${CAMPS.map(diagnosticCard).join('')}</section>
    </div>`;
}
