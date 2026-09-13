export function parseRoute() {
  const parts = (location.hash.replace(/^#/, '') || '/').split('/').filter(Boolean);
  if (parts[0] === 'diagnostics') return { page: 'diagnostics', campId: null };
  if (parts[0] === 'field' && parts[1]) return { page: 'field', campId: parts[1] };
  return { page: 'home', campId: null };
}

export function go(page, campId = null) {
  if (page === 'diagnostics') location.hash = '#/diagnostics';
  else if (page === 'field') location.hash = `#/field/${campId}`;
  else location.hash = '#/';
}
