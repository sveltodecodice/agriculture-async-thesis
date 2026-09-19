# Plantation Sensor

## Scopo

Il `Plantation Sensor` rappresenta la coltura presente in un campo e ne osserva il ciclo di vita. Combina telemetria ambientale e del terreno con gli eventi generati da Seminatrice e Raccoglitore, calcolando crescita e stato di salute della piantagione.

## Responsabilità architetturali

Il servizio **osserva la piantagione**. Non decide quale coltura seminare e non esegue direttamente semina o raccolta. La Seminatrice pubblica l'evento `seeded`, il Raccoglitore pubblica `harvested`, mentre il sensore aggiorna lo stato osservato.

L'avanzamento della crescita avviene quando cambia la data simulata ricevuta dall'Ambient Sensor, non in base al tempo reale del container.

## Logica e flusso dati

```text
Terrain Sensor ── terrain/telemetry ──┐
Ambient Sensor ─ environment/telemetry ├─→ Plantation Sensor
Seeder ─────── plantation/event/seeded ┤
Harvester ─ plantation/event/harvested ┘
                         ↓
              stato e salute coltura
                         ↓
           camp/{field}/plantation/status
                         ↓
            Gestore centrale + Dashboard
```

L'evento `cleared` permette di svuotare lo stato della coltura. Il catalogo delle colture deriva dalla configurazione comune `farm.yaml`, evitando cataloghi divergenti tra servizi.

## Topic MQTT principali

| Direzione | Topic | Utilizzo |
|---|---|---|
| Sottoscrive | `camp/{field}/terrain/telemetry` | Umidità del terreno |
| Sottoscrive | `camp/{field}/environment/telemetry` | Temperatura, stagione e data |
| Sottoscrive | `camp/{field}/plantation/event/seeded` | Semina completata |
| Sottoscrive | `camp/{field}/plantation/event/harvested` | Raccolta completata |
| Sottoscrive | `camp/{field}/plantation/event/cleared` | Svuotamento richiesto dal Gestore centrale |
| Pubblica | `camp/{field}/plantation/status` | Stato completo della coltura |
| Pubblica | `camp/{field}/heartbeat/plantation_sensor` | Presenza servizio |

Lo stato della coltura viene pubblicato in un unico payload strutturato su `plantation/status`. I precedenti topic scalari `plant_name`, `time_left`, `growth_stage` e `health`, che non avevano subscriber interni, sono stati rimossi. È stato rimosso anche l'evento amministrativo `reset`, privo di publisher nel deployment corrente. Gli stati di crescita restano intenzionalmente in inglese, ad esempio `GERMINATION`, `VEGETATIVE` e `READY_FOR_HARVEST`; la Dashboard li localizza in fase di presentazione.

## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


Le proprietà più importanti sono il catalogo `crops`, `simulation.plantation_publish_interval_seconds` e `health.publish_interval_seconds`.

## Struttura del modulo

La logica agronomica è concentrata in `src/core/plant_conditions.py`: creazione stato, semina osservata, avanzamento dei giorni, fase di crescita, salute e svuotamento del campo. `src/main.py` integra questi calcoli con MQTT.

## Dipendenze

- `aiomqtt`;
- `PyYAML`;
- `pytest`.


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

Esiste una replica per ogni campo. Ogni replica osserva solo i topic associati al proprio `FIELD_NAME`.
