import { loadInitialData, openStateStream } from './api.js';
import { bindGlobalNavigation, renderSidebar } from './components.js';
import { parseRoute } from './router.js';
import { store } from './store.js';
import { renderHome } from './pages/home.js';
import { renderField } from './pages/field.js';
import { renderDiagnostics } from './pages/diagnostics.js';

const page = document.getElementById('page');
const sidebar = document.getElementById('sidebar');
const backdrop = document.getElementById('sidebarBackdrop');
const toastElement = document.getElementById('toast');

function toast(message, error = false) {
  toastElement.textContent = message;
  toastElement.style.background = error ? 'var(--red-500)' : 'var(--green-900)';
  toastElement.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => toastElement.classList.remove('show'), 2200);
}

function closeSidebar() { sidebar.classList.remove('open'); backdrop.classList.remove('open'); }
function openSidebar() { sidebar.classList.add('open'); backdrop.classList.add('open'); }

function render() {
  if (!store.snapshot) return;
  store.route = parseRoute();
  renderSidebar();
  if (store.route.page === 'diagnostics') renderDiagnostics(page);
  else if (store.route.page === 'field') renderField(page, store.route.campId, toast);
  else renderHome(page);
}

async function start() {
  bindGlobalNavigation(closeSidebar);
  document.getElementById('menuButton').addEventListener('click', openSidebar);
  backdrop.addEventListener('click', closeSidebar);
  window.addEventListener('hashchange', render);

  try {
    const initial = await loadInitialData();
    store.snapshot = initial.snapshot;
    store.crops = initial.crops;
    render();
    openStateStream((snapshot) => { store.snapshot = snapshot; render(); }, () => toast('Connessione live in aggiornamento…'));
  } catch (error) {
    page.innerHTML = `<div class="card"><h3>Dashboard non disponibile</h3><p>${error.message}</p></div>`;
  }
}

start();
