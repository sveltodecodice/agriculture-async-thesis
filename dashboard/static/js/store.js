export const store = {
  snapshot: null,
  crops: [],
  route: { page: 'home', campId: null },
};

// Field topology comes from the backend snapshot, which in turn is configured
// through CAMP_IDS. The browser therefore does not duplicate the deployment list.
export function campIds() {
  const camps = store.snapshot?.camps;
  if (!camps || typeof camps !== 'object') return [];
  return Object.keys(camps).filter((campId) => camps[campId] && typeof camps[campId] === 'object');
}

// Snapshots arrive asynchronously through SSE. A field may be temporarily
// unavailable while the dashboard is starting or topology is changing, so UI
// modules must never dereference a camp directly from the raw snapshot.
export function campState(campId) {
  return store.snapshot?.camps?.[campId] || null;
}