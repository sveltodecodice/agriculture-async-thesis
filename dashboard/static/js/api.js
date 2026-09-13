export async function loadInitialData() {
  const [stateResponse, cropsResponse] = await Promise.all([
    fetch('/api/state'),
    fetch('/api/crops'),
  ]);
  if (!stateResponse.ok || !cropsResponse.ok) throw new Error('Impossibile caricare i dati');
  return {
    snapshot: await stateResponse.json(),
    crops: (await cropsResponse.json()).crops || [],
  };
}

export function openStateStream(onState, onError) {
  const source = new EventSource('/api/events');
  source.addEventListener('state', (event) => onState(JSON.parse(event.data)));
  source.onerror = () => onError?.();
  return source;
}

export async function sendCommand(campId, action, params = {}) {
  const response = await fetch(`/api/camps/${campId}/commands/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Comando non inviato');
  return data;
}
