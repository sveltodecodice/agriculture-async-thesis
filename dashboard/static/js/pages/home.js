import { campIds, campState, store } from '../store.js';
import { clamp, farmDate, fieldPresentation, percentFraction, safe, stageLabel, suggestedAction } from '../format.js';
import { statusPill } from '../components.js';

const tones = ['green', 'sand', 'orange'];

function timeLeft(plant) {
  if (plant.time_left === null || plant.time_left === undefined) return '—';
  return `${Math.max(0, Number(plant.time_left))} g`;
}

function fieldCard(campId, index) {
  const camp = campState(campId) || {};
  const plant = camp.plantation || {};
  const terrain = camp.terrain || {};
  const presentation = fieldPresentation(camp);
  const recommendation = suggestedAction(camp);
  const growth = clamp(Number(plant.growth_percentage || 0), 0, 100);

  return `
    <article class="card field-card ${tones[index]}" data-field-link="${campId}">
      <div class="field-accent"></div>
      <div class="field-card-content">
        <div class="card-header">
          <div>
            <p class="card-kicker">${campId.toUpperCase()}</p>
            <h3 class="field-crop">${safe(plant.crop || 'Nessuna')}</h3>
          </div>
          ${statusPill(presentation.tone, presentation.label)}
        </div>
        <p class="field-state-text">${safe(presentation.description)}</p>
        <div class="suggested-action ${recommendation.tone}">
          <span class="suggested-action-label">Azione suggerita</span>
          <strong>${safe(recommendation.label)}</strong>
          <span>${safe(recommendation.description)}</span>
        </div>
        <div class="kpi-grid">
          <div class="kpi-card">
            <span class="kpi-label">Fase</span>
            <strong class="kpi-value textual">${safe(stageLabel(plant.growth_stage))}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">Umidità suolo</span>
            <strong class="kpi-value">${percentFraction(terrain.soil_moisture)}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">Raccolto</span>
            <strong class="kpi-value">${timeLeft(plant)}</strong>
          </div>
        </div>
        <div class="field-card-footer">
          <div class="progress" aria-label="Crescita ${growth}%"><div style="width:${growth}%"></div></div>
        </div>
      </div>
    </article>`;
}

export function renderHome(page) {
  page.className = 'page page-home';
  const mqtt = Boolean(store.snapshot.mqtt?.connected);
  const manager = Boolean(store.snapshot.camp_manager?.connected);
  const camps = campIds();
  const views = camps.map((id) => fieldPresentation(campState(id) || {}));
  const healthy = views.filter((item) => item.tone === 'good').length;
  const attention = camps.length - healthy;
  const ready = camps.filter((id) => String(campState(id)?.plantation?.growth_stage || '').toUpperCase() === 'READY_FOR_HARVEST').length;

  document.getElementById('pageKicker').textContent = 'Smart Farm';
  document.getElementById('pageTitle').textContent = 'Panoramica azienda';
  document.getElementById('topbarTools').innerHTML = `
    <span class="tool-pill">${farmDate(store.snapshot)}</span>
    ${statusPill(mqtt ? 'good' : 'bad', mqtt ? 'MQTT online' : 'MQTT offline')}
    ${statusPill(manager ? 'good' : 'bad', manager ? 'Manager online' : 'Manager offline')}`;

  page.innerHTML = `
    <div class="content-stack">
      <article class="card dark summary-card">
        <div class="summary-copy">
          <p class="card-kicker">Stato azienda</p>
          <h2>${attention ? `${attention} ${attention === 1 ? 'campo richiede' : 'campi richiedono'} attenzione` : 'Tutti i campi sono regolari'}</h2>
          <p class="body-copy">Una lettura sintetica dello stato delle colture e dei servizi. Apri un campo solo quando servono dettagli o comandi.</p>
        </div>
        <div class="summary-stat"><span>Campi regolari</span><strong>${healthy}/${camps.length}</strong></div>
        <div class="summary-stat"><span>Da controllare</span><strong>${attention}</strong></div>
        <div class="summary-stat"><span>Pronti al raccolto</span><strong>${ready}</strong></div>
      </article>

      <div class="section-heading">
        <div>
          <h2>Campi</h2>
          <p>Coltura corrente, condizione e tre indicatori essenziali.</p>
        </div>
      </div>

      <section class="home-fields">
        ${camps.map(fieldCard).join('')}
      </section>

      <article class="card sand">
        <div class="card-header">
          <div>
            <p class="card-kicker">Sistema</p>
            <h3>Connessioni e diagnostica</h3>
            <p class="body-copy">MQTT e Camp Manager sono mostrati nella barra superiore. La diagnostica raccoglie lo stato dei sensori di ogni campo.</p>
          </div>
          ${statusPill(mqtt && manager ? 'good' : 'warn', mqtt && manager ? 'Sistema connesso' : 'Connessione da verificare')}
        </div>
        <button class="secondary-button" data-route="diagnostics">Apri diagnostica</button>
      </article>
    </div>`;
}
