# Ambient Sensor

## Scopo

L'`Ambient Sensor` simula le condizioni atmosferiche osservate in un campo della Smart Farm. Il suo compito principale è produrre dati ambientali coerenti con stagione e data simulata e pubblicarli tramite MQTT. È inoltre il proprietario dell'orologio della simulazione: l'avanzamento manuale dei giorni viene quindi inviato direttamente a questo servizio e non al Gestore centrale.

## Responsabilità architetturali

Il servizio **osserva e simula l'ambiente**, ma non decide azioni agronomiche. Genera temperatura, umidità dell'aria, meteo, pioggia, vento e radiazione. Mantiene data e stagione del campo e pubblica periodicamente la telemetria. Espone anche i comandi amministrativi per avanzare o reimpostare il tempo simulato.

Non deve decidere irrigazioni, semine o raccolti. Queste decisioni appartengono al Gestore centrale o agli attuatori dedicati.

## Logica e flusso dati

```text
farm.yaml / ENV
      ↓
Ambient Sensor
      ↓
calcolo data, stagione e condizioni ambientali
      ↓
camp/{field}/environment/telemetry
      ↓
Terrain Sensor + Plantation Sensor + Gestore centrale + Dashboard
```

A ogni ciclo il servizio pubblica lo stato corrente e poi calcola il passo ambientale successivo. Il comando `skip` fa avanzare il calendario simulato di uno o più giorni e pubblica i nuovi valori. Il comando `reset` riporta il calendario alla data iniziale configurata.

## Topic MQTT principali

| Direzione | Topic | Utilizzo |
|---|---|---|
| Pubblica | `camp/{field}/environment/telemetry` | Telemetria ambientale corrente |
| Sottoscrive | `camp/{field}/environment/cmd/#` | Comandi `skip` e `reset` |
| Pubblica | `camp/{field}/heartbeat/ambient_sensor` | Presenza del servizio per Stato Sistema |

L'heartbeat contiene anche un timestamp della sorgente. Questo permette alla Dashboard di riconoscere immediatamente un heartbeat retained ormai vecchio dopo un riavvio.


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


Le proprietà più rilevanti sono `simulation.start_date`, `simulation.environment_publish_interval_seconds`, le fasce stagionali in `environment.*` e `health.publish_interval_seconds`. Gli override principali sono `SIMULATION_START_DATE`, `ENV_PUBLISH_INTERVAL_SECONDS`, `HEARTBEAT_INTERVAL_SECONDS` e le variabili MQTT comuni.

## Struttura del modulo

`src/core/manager.py` coordina lo stato ambientale. I file `temperature.py`, `weather.py`, `air_humidity.py`, `wind.py`, `radiation.py` e `season.py` contengono funzioni semplici per le singole grandezze. `src/main.py` gestisce il ciclo asincrono, MQTT, heartbeat e riconnessione.

## Dipendenze

- `aiomqtt`: client MQTT asincrono;
- `PyYAML`: lettura di `farm.yaml`;
- `pytest`: test di regressione.


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

Il Compose crea una replica per ogni campo e passa `FIELD_NAME`. Il comando del container è definito nel `Dockerfile` del modulo. Normalmente il servizio viene avviato insieme all'intero sistema con `docker compose up -d`.