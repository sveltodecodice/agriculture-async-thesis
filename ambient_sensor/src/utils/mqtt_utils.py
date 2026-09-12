"""
Helpers condivisi tra i servizi MQTT del progetto:
- publish_json: pubblica un dict come JSON, timbrato con un timestamp
  wall-clock ("ts"), cosi' tutti i servizi usano lo stesso formato.
- Deduper: tiene traccia dell'ultimo timestamp visto PER TOPIC, cosi'
  un servizio puo' scartare messaggi duplicati o piu' vecchi di uno
  gia' processato.

IMPORTANTE: ogni servizio deve avere la PROPRIA istanza di Deduper.
Non condividere la stessa istanza tra servizi diversi (es. plantation
e camp_manager sono entrambi sottoscritti a camp/terrain_telemetry,
ma processano in modo indipendente e devono avere memoria separata).
"""

import time
import json


class Deduper:
    def __init__(self):
        self._last_seen: dict[str, float] = {}

    def is_duplicate_or_stale(self, topic: str, ts) -> bool:
        """Ritorna True se il messaggio va scartato (stesso ts o piu' vecchio
        dell'ultimo visto su quel topic). Se il ts manca o e' malformato,
        il messaggio NON viene bloccato (fail-open) ma nemmeno tracciato."""
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            return False

        prev = self._last_seen.get(topic)
        if prev is not None and ts <= prev:
            return True
        self._last_seen[topic] = ts
        return False

    def reset(self, topic: str | None = None):
        """Da chiamare sui comandi di reset, cosi' un messaggio legittimo
        post-reset non viene rigettato come 'stale' per errore."""
        if topic is None:
            self._last_seen.clear()
        else:
            self._last_seen.pop(topic, None)


async def publish_json(client, topic, payload: dict, **kwargs):
    """Pubblica un dict come JSON aggiungendo il campo 'ts' (time.time()).
    Usare questa funzione al posto di client.publish(topic, json.dumps(...))
    ovunque, cosi' il timestamp e' sempre presente e nello stesso formato."""
    stamped = {**payload, "ts": time.time()}
    await client.publish(topic, json.dumps(stamped), **kwargs)