# Dashboard Smart Farm

Versione minimale, localizzata in italiano e con aggiornamento incrementale.

## Principi

- Backend MQTT basato esclusivamente su `aiomqtt`.
- Un solo file JavaScript (`static/app.js`).
- Un solo foglio stile (`static/styles.css`).
- Aggiornamento dello stato ogni 2 secondi.
- Gli aggiornamenti modificano solo le sezioni dati della vista corrente.
- I controlli operatore non vengono ricreati durante il polling.
- Interfaccia visibile completamente in italiano.
- Diagnostica separata dalla panoramica agronomica.

## Operazioni del campo

La scheda Operazioni è divisa in quattro sezioni:

1. Irrigazione
2. Semina
3. Simulazione
4. Manutenzione

La semina mostra per impostazione predefinita soltanto le colture ideali per
stagione e terreno. L'opzione "Mostra tutte le colture" rende visibili tutte
le alternative, evidenziando compatibilità di terreno, stagione, umidità e
temperatura.

## Aggiornamento dati

La dashboard interroga `/api/state` ogni 2 secondi. Quando cambia la
revisione dello stato:

- Panoramica: aggiorna i tre blocchi informativi.
- Campo: aggiorna solamente i dati nella colonna principale e gli indicatori
  operativi necessari.
- Attività: aggiorna gli elenchi.
- Diagnostica: aggiorna lo stato tecnico.

La scheda operativa selezionata, il filtro delle colture, la coltura
selezionata e gli input dell'operatore vengono mantenuti.
