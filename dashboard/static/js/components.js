import { campIds, campState, store } from './store.js';
import { fieldPresentation, safe } from './format.js';
import { go } from './router.js';

export function statusPill(tone, label) {
  return `<span class="status-pill ${tone}"><span class="dot"></span>${safe(label)}</span>`;
}

export function renderSidebar() {
  document.querySelectorAll('[data-route]').forEach((button) => {
    button.classList.toggle('active', button.dataset.route === store.route.page);
  });
  const camps = campIds();
  document.getElementById('fieldNav').innerHTML = camps.map((campId) => {
    const camp = campState(campId) || {};
    const view = fieldPresentation(camp);
    const active = store.route.page === 'field' && store.route.campId === campId;
    return `
      <button class="field-nav-button ${active ? 'active' : ''}" data-field-link="${campId}">
        <span class="field-nav-copy"><strong>${campId.toUpperCase()}</strong><span>${safe(camp.plantation?.crop || 'Nessuna')}</span></span>
        <span class="field-nav-dot ${view.tone === 'good' ? 'good' : view.tone === 'warn' ? 'warn' : view.tone === 'bad' ? 'bad' : ''}"></span>
      </button>`;
  }).join('');

  const mqtt = Boolean(store.snapshot?.mqtt?.connected);
  const manager = Boolean(store.snapshot?.camp_manager?.connected);
  document.getElementById('sidebarSystem').innerHTML = `
    <div class="system-row"><span>MQTT</span><strong>${mqtt ? 'Online' : 'Offline'}</strong></div>
    <div class="system-row"><span>Camp Manager</span><strong>${manager ? 'Online' : 'Offline'}</strong></div>`;
}

export function bindGlobalNavigation(closeSidebar) {
  document.addEventListener('click', (event) => {
    const route = event.target.closest('[data-route]');
    if (route) { go(route.dataset.route); closeSidebar?.(); return; }
    const field = event.target.closest('[data-field-link]');
    if (field) { go('field', field.dataset.fieldLink); closeSidebar?.(); }
  });
}
