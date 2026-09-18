# Dashboard

## Scopo

La `Dashboard` è l'interfaccia web della Smart Farm. Presenta i dati simulati in italiano, permette di consultare lo stato agronomico, mostra la topologia tecnica del sistema e consente all'operatore di inviare azioni manuali. La Dashboard non sostituisce il Gestore centrale: invia intenzioni, mentre la logica decisionale rimane nel backend MQTT.

## Responsabilità architetturali

La Dashboard deve **visualizzare senza inventare stato**. Le informazioni tecniche vengono mostrate in `Stato Sistema`, mentre le informazioni agronomiche rimangono in `Panoramica` e nel dettaglio del singolo campo. `Notifiche Sistema` raccoglie decisioni, eventi e richieste operatore.

Il menu principale contiene solamente:

```text
Panoramica
Stato Sistema
Notifiche Sistema
```

La data simulata viene mostrata soltanto nel blocco `Meteo corrente`, perché appartiene al contesto ambientale e non deve essere ripetuta come indicatore globale.

## Flusso dati

```text
Sensori / attuatori / Gestore centrale
                ↓ MQTT/TLS QoS 2
             Dashboard backend
                ↓ stato normalizzato
          API separate per pagina
                ↓ polling incrementale
             interfaccia web
```

Il frontend aggiorna solo la vista interessata quando cambia la revisione dello stato. I controlli dell'operatore, il seme selezionato e i campi di input non vengono ricreati inutilmente durante gli aggiornamenti della telemetria.

## API HTTP

La Dashboard evita un endpoint monolitico per ridurre la possibilità di mostrare o trasferire informazioni non coerenti con la pagina:

| Endpoint | Contenuto |
|---|---|
| `GET /api/overview` | Meteo, terreno e colture necessari alla Panoramica |
| `GET /api/camps/{field}` | Dettaglio del solo campo selezionato |
| `GET /api/notifications` | Notifiche, eventi e comandi dell'operatore |
| `GET /api/system-status` | Topologia, connessioni e heartbeat |
| `GET /api/crops` | Catalogo selezionabile dalla UI |
| `GET /api/config` | Intervallo di polling frontend |
| `GET /healthz` | Stato sintetico del backend |
| `POST /api/camps/{field}/commands/{action}` | Invio comando operatore |

`/api/system-status` non espone password, credenziali, payload MQTT, lista delle sottoscrizioni o errori tecnici grezzi.

## Instradamento dei comandi

I comandi `plant`, `irrigate`, `reoxygenate`, `clear` e `restart` vengono inviati al Gestore centrale. Il comando `skip` va direttamente all'Ambient Sensor perché quest'ultimo è proprietario dell'orologio simulato.

## Localizzazione degli stati

I contratti MQTT mantengono stati macchina stabili in inglese. `static/app.js` li traduce centralmente in italiano. Sono gestiti, tra gli altri:

- crescita: `EMPTY`, `PLANTED`, `GERMINATION`, `VEGETATIVE`, `MATURING`, `READY_FOR_HARVEST`;
- salute: `HEALTHY`, `FIELD IS EMPTY`, `TOO_DRY`, `TOO_WET`, `TOO_COLD`, `TOO_HOT`, `UNFAVORABLE_SEASON`;
- servizi: `ONLINE`, `OFFLINE`, `UNKNOWN`;
- sistema: `HEALTHY`, `DEGRADED`, `UNKNOWN`;
- operazioni Irrigator: `idle`, `irrigating`, `reoxygenating`;
- comandi ed eventi principali.

Gli stati sconosciuti non vengono mostrati copiando una stringa inglese non prevista: la UI usa un fallback italiano `Sconosciuto/Sconosciuta`.

## Stato Sistema e heartbeat

La pagina `Stato Sistema` usa heartbeat reali di Ambient Sensor, Terrain Sensor, Plantation Sensor, Seeder e Harvester, lo status periodico dell'Irrigator e `camp/manager/status` per il Gestore centrale. La freschezza viene calcolata usando il timestamp della sorgente; in mancanza di un timestamp valido il backend usa in modo prudente il momento di ricezione. Uno stato retained vecchio non viene quindi considerato indefinitamente online.

## Selezione colture

La pagina campo mostra per impostazione predefinita le colture ideali per stagione e terreno. L'operatore può attivare `Mostra tutte le colture` e vedere anche le alternative, con indicatori separati per terreno, stagione, umidità e temperatura. I nomi delle colture conosciute vengono localizzati usando il catalogo comune `farm.yaml`.


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


I parametri principali sono `dashboard.port`, `dashboard.polling_interval_seconds`, `dashboard.mqtt_client_id`, `farm.fields`, `health.*` e la configurazione MQTT.

## Struttura del modulo

Il backend Python si trova in `src/`. `state_store.py` conserva lo snapshot, `message_handlers.py` applica i messaggi MQTT, `view_data.py` costruisce payload coerenti per ciascuna vista, `http_server.py` espone API e file statici. Il frontend rimane volutamente semplice: un solo `static/app.js` e un solo `static/styles.css`.

## Dipendenze

- `aiomqtt`;
- `PyYAML`;
- `pytest`;
- API standard Python `http.server` per il server HTTP.


## Sicurezza e affidabilità

La comunicazione MQTT usa `aiomqtt` con TLS verificato. Il certificato della CA viene caricato dal percorso configurato, la verifica dell'hostname è attiva e la versione minima predefinita è TLS 1.2. Il progetto impone MQTT QoS 2 per pubblicazioni e sottoscrizioni che fanno parte del flusso applicativo. Il client usa un identificativo stabile, `clean_session=False`, keepalive e un ciclo di riconnessione continuo.

Il container parte dopo che il broker ha superato il proprio healthcheck TLS/MQTT. Il servizio è inoltre controllato dal healthcheck comune montato in `/app/mqtt_tls_healthcheck.py`, che esegue una vera connessione MQTT su TLS e una chiusura regolare della sessione.



## Test

I test sono contenuti nella directory `tests/` e usano Pytest. Come convenzione di progetto, ogni file di test raggiunge il codice applicativo con:

```python
import sys
sys.path.append("src")
```

Per eseguire i test del solo modulo:

```bash
pytest -q
```

I test non richiedono un broker MQTT reale per verificare la logica core. Le verifiche di rete vengono limitate ai controlli statici o alle funzioni pure, così la suite resta veloce e semplice da mantenere.


## Avvio in Docker

La Dashboard espone la porta configurata, normalmente `8501`, solo su localhost nel Compose. Per ricostruire il solo componente: `docker compose build dashboard` seguito da `docker compose up -d --force-recreate dashboard`.