export const safe = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const number = (value) => (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) ? null : Number(value);
export const percentFraction = (value, digits = 0) => number(value) === null ? '—' : `${(Number(value) * 100).toFixed(digits)}%`;
export const percentNumber = (value, digits = 0) => number(value) === null ? '—' : `${Number(value).toFixed(digits)}%`;
export const valueWithUnit = (value, unit, digits = 1) => number(value) === null ? '—' : `${Number(value).toFixed(digits)}${unit}`;
export const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const stageLabels = {
  EMPTY: 'Campo libero',
  GERMINATION: 'Germinazione',
  SEEDLING: 'Plantula',
  VEGETATIVE: 'Crescita vegetativa',
  FLOWERING: 'Fioritura',
  FRUITING: 'Fruttificazione',
  MATURE: 'Matura',
  MATURING: 'Maturazione',
  READY_FOR_HARVEST: 'Pronta al raccolto',
};

export function stageLabel(raw) {
  const key = String(raw || '').toUpperCase();
  return stageLabels[key] || raw || 'Stato non disponibile';
}

function numericCheck({ key, label, value, min = null, max = null, unit = '', formatter, domainMin = null, domainMax = null }) {
  const actual = number(value);
  const minimum = number(min);
  const maximum = number(max);
  let state = 'unknown';

  if (actual !== null) {
    if (minimum !== null && actual < minimum) state = 'low';
    else if (maximum !== null && actual > maximum) state = 'high';
    else if (minimum !== null || maximum !== null) state = 'ok';
    else state = 'info';
  }

  const expected = minimum !== null && maximum !== null
    ? `${formatter(minimum)} – ${formatter(maximum)}`
    : minimum !== null
      ? `≥ ${formatter(minimum)}`
      : maximum !== null
        ? `≤ ${formatter(maximum)}`
        : 'Solo informativo';

  let note = 'Dato non disponibile';
  if (actual !== null) {
    if (state === 'ok') note = 'Valore nel range atteso';
    else if (state === 'low' && minimum !== null) note = `${formatter(minimum - actual)} sotto il minimo`;
    else if (state === 'high' && maximum !== null) note = `${formatter(actual - maximum)} sopra il massimo`;
    else if (state === 'info') note = 'Valore informativo';
  }

  return {
    key,
    label,
    actual,
    min: minimum,
    max: maximum,
    unit,
    state,
    expected,
    note,
    valueText: actual === null ? '—' : formatter(actual),
    domainMin,
    domainMax,
  };
}

function soilCheck(current, ideal) {
  const currentText = String(current || '').trim();
  const idealText = String(ideal || '').trim();
  if (!currentText) return { key: 'soil_type', label: 'Tipo terreno', state: 'unknown', valueText: '—', expected: idealText || '—', note: 'Dato non disponibile' };
  if (!idealText) return { key: 'soil_type', label: 'Tipo terreno', state: 'info', valueText: currentText, expected: 'Nessun riferimento', note: 'Valore informativo' };
  const ok = currentText.toLowerCase() === idealText.toLowerCase();
  return {
    key: 'soil_type',
    label: 'Tipo terreno',
    state: ok ? 'ok' : 'mismatch',
    valueText: currentText,
    expected: idealText,
    note: ok ? 'Terreno compatibile con la coltura' : `Ideale: ${idealText}`,
  };
}

/**
 * Crop-aware checks used by status, recommendations and telemetry cards.
 * The crop thresholds are injected by the Python normalizer, so the UI does
 * not need to guess them from the displayed crop name.
 */
export function fieldChecks(camp) {
  const env = camp?.environment || {};
  const terrain = camp?.terrain || {};
  const plant = camp?.plantation || {};

  const moisture = numericCheck({
    key: 'soil_moisture',
    label: 'Umidità suolo',
    value: terrain.soil_moisture,
    min: plant.min_moisture,
    max: plant.max_moisture,
    formatter: (v) => percentFraction(v),
    domainMin: 0,
    domainMax: 1,
  });

  if (moisture.actual !== null && moisture.state === 'high' && moisture.max !== null) {
    moisture.note = `${((moisture.actual - moisture.max) * 100).toFixed(0)} punti percentuali sopra il massimo`;
  } else if (moisture.actual !== null && moisture.state === 'low' && moisture.min !== null) {
    moisture.note = `${((moisture.min - moisture.actual) * 100).toFixed(0)} punti percentuali sotto il minimo`;
  }

  const temperature = numericCheck({
    key: 'temperature',
    label: 'Temperatura',
    value: env.temperature,
    min: plant.min_temperature,
    max: plant.max_temperature,
    formatter: (v) => `${Number(v).toFixed(1)} °C`,
    domainMin: plant.min_temperature !== null && plant.min_temperature !== undefined ? Number(plant.min_temperature) - 10 : 0,
    domainMax: plant.max_temperature !== null && plant.max_temperature !== undefined ? Number(plant.max_temperature) + 10 : 40,
  });

  const oxygen = numericCheck({
    key: 'oxygenation',
    label: 'Ossigenazione',
    value: terrain.oxygenation,
    min: 30,
    max: null,
    formatter: (v) => `${Number(v).toFixed(1)}%`,
    domainMin: 0,
    domainMax: 100,
  });

  const soil = soilCheck(terrain.soil_type, plant.ideal_soil);
  return { moisture, temperature, oxygen, soil };
}

export function checkTone(check) {
  if (!check) return 'neutral';
  if (check.state === 'ok') return 'good';
  if (['low', 'high', 'mismatch'].includes(check.state)) return 'warn';
  return 'neutral';
}

export function checkLabel(check) {
  return ({
    ok: 'Nel range',
    low: 'Basso',
    high: 'Alto',
    mismatch: 'Non ideale',
    info: 'Informativo',
    unknown: 'Dato assente',
  })[check?.state] || '—';
}

export function rangeGeometry(check) {
  if (!check || number(check.actual) === null || number(check.domainMin) === null || number(check.domainMax) === null) return null;
  const span = Number(check.domainMax) - Number(check.domainMin);
  if (span <= 0) return null;
  const pct = (v) => clamp(((Number(v) - Number(check.domainMin)) / span) * 100, 0, 100);
  const actual = pct(check.actual);
  const start = check.min === null ? 0 : pct(check.min);
  const end = check.max === null ? 100 : pct(check.max);
  return { actual, start, width: Math.max(0, end - start) };
}

function issueText(check) {
  if (!check || !['low', 'high', 'mismatch'].includes(check.state)) return null;
  if (check.key === 'soil_moisture') {
    if (check.state === 'low') return `umidità ${check.valueText}, sotto ${check.expected}`;
    return `umidità ${check.valueText}, sopra ${check.expected}`;
  }
  if (check.key === 'temperature') {
    if (check.state === 'low') return `temperatura ${check.valueText}, sotto ${check.expected}`;
    return `temperatura ${check.valueText}, sopra ${check.expected}`;
  }
  if (check.key === 'oxygenation') return `ossigenazione ${check.valueText}, atteso ${check.expected}`;
  if (check.key === 'soil_type') return `terreno ${check.valueText}, ideale ${check.expected}`;
  return null;
}

export function fieldPresentation(camp) {
  const plant = camp?.plantation || {};
  const health = String(plant.health || '').toUpperCase();
  const stage = String(plant.growth_stage || '').toUpperCase();
  const checks = fieldChecks(camp);
  const issues = Object.values(checks).filter((check) => ['low', 'high', 'mismatch'].includes(check.state));

  if (!plant.occupied || health.includes('EMPTY')) {
    return { tone: 'neutral', label: 'Campo libero', description: 'Il campo è disponibile per una nuova coltura.' };
  }
  if (stage === 'READY_FOR_HARVEST' || number(plant.time_left) === 0) {
    return { tone: 'good', label: 'Pronto al raccolto', description: `${plant.crop} ha completato il ciclo di crescita.` };
  }
  if (issues.length) {
    const first = issueText(issues[0]);
    const extra = issues.length > 1 ? ` Altri ${issues.length - 1} parametri sono fuori range.` : '';
    return { tone: 'warn', label: 'Da monitorare', description: `${first ? first.charAt(0).toUpperCase() + first.slice(1) : 'Parametri fuori range.'}.${extra}` };
  }
  if (health.includes('TOO_DRY') || health.includes('TOO_WET')) {
    return { tone: 'warn', label: 'Da monitorare', description: `Il backend segnala ${health.replaceAll('_', ' ').toLowerCase()}.` };
  }
  return { tone: 'good', label: 'Regolare', description: `${plant.crop} procede regolarmente: ${stageLabel(stage).toLowerCase()}.` };
}

/**
 * Choose one useful intervention from the commands that actually exist.
 * Priority is: crop lifecycle -> low oxygen -> low moisture -> simulation step
 * for environmental values that cannot be corrected directly -> no action.
 */
export function suggestedAction(camp) {
  const plant = camp?.plantation || {};
  const terrain = camp?.terrain || {};
  const health = String(plant.health || '').toUpperCase();
  const stage = String(plant.growth_stage || '').toUpperCase();
  const checks = fieldChecks(camp);

  if (!plant.occupied || health.includes('EMPTY')) {
    return {
      key: 'plant',
      command: 'plant',
      params: null,
      button: null,
      tone: 'neutral',
      label: 'Semina una coltura',
      description: 'Il campo è libero. Seleziona la coltura nel pannello azioni.',
    };
  }

  if (stage === 'READY_FOR_HARVEST' || number(plant.time_left) === 0) {
    return {
      key: 'auto_harvest',
      command: null,
      params: null,
      button: null,
      tone: 'good',
      label: 'Attendi il raccolto automatico',
      description: 'Il Camp Manager gestisce automaticamente raccolta e successivo svuotamento.',
    };
  }

  if (checks.oxygen.state === 'low') {
    return {
      key: 'reoxygenate',
      command: 'reoxygenate',
      params: {},
      button: 'Riossigena ora',
      tone: 'warn',
      label: 'Riossigena il terreno',
      description: `Ossigenazione ${checks.oxygen.valueText}; la soglia operativa è ${checks.oxygen.expected}.`,
    };
  }

  if (checks.moisture.state === 'low') {
    if (terrain.irrigation_active === true) {
      return {
        key: 'wait_irrigation',
        command: null,
        params: null,
        button: null,
        tone: 'warn',
        label: 'Attendi il ciclo di irrigazione',
        description: `Umidità ${checks.moisture.valueText}, target ${checks.moisture.expected}; l'irrigazione risulta già attiva.`,
      };
    }
    return {
      key: 'irrigate',
      command: 'irrigate',
      params: {},
      button: 'Irriga ora',
      tone: 'warn',
      label: 'Irriga il campo',
      description: `Umidità ${checks.moisture.valueText}, sotto il target ${checks.moisture.expected}.`,
    };
  }

  const environmentalIssues = [checks.moisture, checks.temperature].filter((check) => ['low', 'high'].includes(check.state));
  if (environmentalIssues.length) {
    const details = environmentalIssues.map(issueText).filter(Boolean).join('; ');
    const tooWet = checks.moisture.state === 'high';
    return {
      key: 'advance_and_recheck',
      command: 'skip',
      params: { days: 1 },
      button: 'Avanza 1 giorno',
      tone: 'warn',
      label: tooWet ? 'Non irrigare; avanza 1 giorno' : 'Avanza la simulazione e rivaluta',
      description: `${details}. ${tooWet ? 'Evita nuova irrigazione. ' : ''}Non c'è un comando diretto per correggere questi valori; avanza 1 giorno e ricontrolla la telemetria.`,
    };
  }

  if (checks.soil.state === 'mismatch') {
    return {
      key: 'soil_mismatch',
      command: null,
      params: null,
      button: null,
      tone: 'warn',
      label: 'Mantieni il terreno sotto osservazione',
      description: `Terreno attuale ${checks.soil.valueText}; per ${plant.crop} il riferimento è ${checks.soil.expected}. Il Camp Manager non espone un comando di cambio terreno.`,
    };
  }

  return {
    key: 'none',
    command: null,
    params: null,
    button: null,
    tone: 'good',
    label: 'Nessuna azione necessaria',
    description: 'Umidità, temperatura e ossigenazione sono compatibili con i riferimenti disponibili.',
  };
}

export function farmDate(snapshot) {
  for (const camp of Object.values(snapshot?.camps || {})) {
    if (camp?.environment?.date) return camp.environment.date;
  }
  return 'Data non disponibile';
}
