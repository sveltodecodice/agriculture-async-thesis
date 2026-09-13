import { store } from '../store.js';
import {
  checkLabel,
  checkTone,
  fieldChecks,
  fieldPresentation,
  percentFraction,
  percentNumber,
  rangeGeometry,
  safe,
  stageLabel,
  suggestedAction,
  valueWithUnit,
} from '../format.js';
import { statusPill } from '../components.js';
import { sendCommand } from '../api.js';

function cropOptions(selected) {
  return store.crops.map((crop) => `<option value="${safe(crop.key)}" ${crop.name === selected ? 'selected' : ''}>${safe(crop.name)}</option>`).join('');
}

function timeLeft(plant) {
  if (plant.time_left === null || plant.time_left === undefined) return '—';
  return `${Math.max(0, Number(plant.time_left))} giorni`;
}

function rangeBar(check) {
  const geometry = rangeGeometry(check);
  if (!geometry) return '';
  return `
    <div class="metric-range" aria-hidden="true">
      <span class="metric-range-expected" style="left:${geometry.start}%;width:${geometry.width}%"></span>
      <span class="metric-range-marker ${checkTone(check)}" style="left:${geometry.actual}%"></span>
    </div>`;
}

function monitoredMetric(check) {
  return `
    <article class="monitored-metric ${checkTone(check)}">
      <div class="monitored-head">
        <span>${safe(check.label)}</span>
        <span class="metric-state ${checkTone(check)}">${safe(checkLabel(check))}</span>
      </div>
      <strong class="monitored-value">${safe(check.valueText)}</strong>
      <div class="metric-reference">
        <span>Atteso</span>
        <strong>${safe(check.expected)}</strong>
      </div>
      ${rangeBar(check)}
      <p>${safe(check.note)}</p>
    </article>`;
}

function soilMetric(check) {
  return `
    <article class="monitored-metric ${checkTone(check)}">
      <div class="monitored-head">
        <span>${safe(check.label)}</span>
        <span class="metric-state ${checkTone(check)}">${safe(checkLabel(check))}</span>
      </div>
      <strong class="monitored-value textual">${safe(check.valueText)}</strong>
      <div class="metric-reference">
        <span>Ideale coltura</span>
        <strong>${safe(check.expected)}</strong>
      </div>
      <p>${safe(check.note)}</p>
    </article>`;
}

function infoMetric(label, value, support) {
  return `
    <div class="info-metric">
      <span>${safe(label)}</span>
      <strong>${safe(value)}</strong>
      <small>${safe(support)}</small>
    </div>`;
}

export function renderField(page, campId, toast) {
  page.className = 'page page-field';
  const camp = store.snapshot.camps[campId];
  if (!camp) { page.innerHTML = '<div class="card"><h3>Campo non trovato.</h3></div>'; return; }

  const env = camp.environment || {};
  const terrain = camp.terrain || {};
  const plant = camp.plantation || {};
  const checks = fieldChecks(camp);
  const presentation = fieldPresentation(camp);
  const recommendation = suggestedAction(camp);

  document.getElementById('pageKicker').textContent = campId.toUpperCase();
  document.getElementById('pageTitle').textContent = plant.crop || 'Campo libero';
  document.getElementById('topbarTools').innerHTML = statusPill(presentation.tone, presentation.label);

  page.innerHTML = `
    <div class="content-stack">
      <div><button class="back-button" data-route="home">← Panoramica</button></div>

      <section class="detail-layout">
        <div class="detail-main">
          <article class="card green plantation-summary">
            <div class="plantation-title">
              <div>
                <p class="card-kicker">Piantagione</p>
                <h2>${safe(plant.crop || 'Nessuna coltura')}</h2>
                <p>${safe(presentation.description)}</p>
              </div>
              ${statusPill(presentation.tone, presentation.label)}
            </div>

            <div class="recommended-action ${recommendation.tone}">
              <div>
                <span>Azione suggerita</span>
                <strong>${safe(recommendation.label)}</strong>
                <p>${safe(recommendation.description)}</p>
              </div>
              ${recommendation.button
                ? `<button class="recommendation-button" id="recommendedActionButton">${safe(recommendation.button)}</button>`
                : ''}
            </div>

            <div class="kpi-grid four">
              <div class="kpi-card"><span class="kpi-label">Crescita</span><strong class="kpi-value">${percentNumber(plant.growth_percentage)}</strong></div>
              <div class="kpi-card"><span class="kpi-label">Fase</span><strong class="kpi-value textual">${safe(stageLabel(plant.growth_stage))}</strong></div>
              <div class="kpi-card"><span class="kpi-label">Raccolto</span><strong class="kpi-value textual">${timeLeft(plant)}</strong></div>
              <div class="kpi-card"><span class="kpi-label">Umidità suolo</span><strong class="kpi-value">${percentFraction(terrain.soil_moisture)}</strong></div>
            </div>
          </article>

          <article class="card telemetry-card">
            <div class="card-header telemetry-title">
              <div>
                <p class="card-kicker">Telemetria</p>
                <h3>Parametri rispetto alla coltura</h3>
                <p class="body-copy">I parametri con un riferimento noto mostrano subito se il valore è nel range atteso.</p>
              </div>
            </div>

            <div class="monitored-grid">
              ${monitoredMetric(checks.moisture)}
              ${monitoredMetric(checks.temperature)}
              ${monitoredMetric(checks.oxygen)}
              ${soilMetric(checks.soil)}
            </div>

            <div class="telemetry-divider"></div>

            <div class="card-header compact-header">
              <div>
                <h4>Contesto ambientale</h4>
                <p class="body-copy">Valori informativi: il progetto non definisce un range specifico per la coltura.</p>
              </div>
            </div>
            <div class="info-grid">
              ${infoMetric('Umidità aria', valueWithUnit(env.humidity_air, '%'), 'Ambiente')}
              ${infoMetric('Pioggia', valueWithUnit(env.rain_mm, ' mm'), 'Ultimo rilievo')}
              ${infoMetric('Vento', valueWithUnit(env.wind_kmh, ' km/h'), 'Ambiente')}
              ${infoMetric('Radiazione', valueWithUnit(env.radiation_wm2, ' W/m²', 0), 'Solare')}
              ${infoMetric('Acqua erogata', valueWithUnit(terrain.water_dispensed_mm, ' mm'), 'Terreno')}
              ${infoMetric('Irrigazione', terrain.irrigation_active === true ? 'Attiva' : terrain.irrigation_active === false ? 'Ferma' : '—', 'Stato pompa')}
            </div>
          </article>
        </div>

        <aside class="detail-side">
          <article class="card sand action-panel">
            <div>
              <p class="card-kicker">Azioni</p>
              <h3>Controlli del campo</h3>
              <p class="body-copy">Comandi manuali effettivamente supportati dal sistema.</p>
            </div>

            <div class="action-section">
              <h4>Intervento rapido</h4>
              <div class="actions-grid">
                <button class="action-button ${recommendation.command === 'irrigate' ? 'recommended' : ''}" data-command="irrigate">Irriga</button>
                <button class="action-button sand ${recommendation.command === 'reoxygenate' ? 'recommended' : ''}" data-command="reoxygenate">Riossigena</button>
              </div>
            </div>

            <div class="action-section">
              <h4>Simulazione</h4>
              <p>Avanza il tempo simulato e acquisisci nuove condizioni ambientali.</p>
              <div class="inline-form">
                <input id="skipDays" type="number" min="1" max="30" value="1" aria-label="Giorni da avanzare">
                <button class="action-button orange ${recommendation.command === 'skip' ? 'recommended' : ''}" id="skipButton">Avanza giorni</button>
              </div>
            </div>

            <div class="action-section">
              <h4>Semina</h4>
              <p>${plant.occupied ? 'Il campo è occupato: la semina sarà disponibile dopo lo svuotamento.' : 'Seleziona la nuova coltura.'}</p>
              <div class="form-group">
                <label for="cropSelect">Coltura</label>
                <select id="cropSelect">${cropOptions(plant.crop)}</select>
                <button class="secondary-button" id="plantButton" ${plant.occupied ? 'disabled' : ''}>Semina</button>
              </div>
            </div>

            <details class="advanced">
              <summary>Manutenzione avanzata</summary>
              <div class="actions-grid advanced-actions">
                <button class="action-button danger" data-command="clear">Svuota campo</button>
                <button class="secondary-button" data-command="restart">Riavvia</button>
              </div>
            </details>
          </article>
        </aside>
      </section>
    </div>`;

  page.querySelectorAll('[data-command]').forEach((button) => button.addEventListener('click', async () => {
    try { await sendCommand(campId, button.dataset.command); toast(`Comando ${button.dataset.command} inviato`); }
    catch (error) { toast(error.message, true); }
  }));

  const recommendedButton = document.getElementById('recommendedActionButton');
  if (recommendedButton && recommendation.command) {
    recommendedButton.addEventListener('click', async () => {
      try {
        await sendCommand(campId, recommendation.command, recommendation.params || {});
        toast(`${recommendation.label}: comando inviato`);
      } catch (error) { toast(error.message, true); }
    });
  }

  document.getElementById('skipButton').addEventListener('click', async () => {
    try {
      await sendCommand(campId, 'skip', { days: Number(document.getElementById('skipDays').value || 1) });
      toast('Avanzamento inviato');
    } catch (error) { toast(error.message, true); }
  });

  document.getElementById('plantButton').addEventListener('click', async () => {
    try {
      await sendCommand(campId, 'plant', { crop_key: document.getElementById('cropSelect').value });
      toast('Comando di semina inviato');
    } catch (error) { toast(error.message, true); }
  });
}
