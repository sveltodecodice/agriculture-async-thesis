# Terrain Sensor

## Scopo

Il `Terrain Sensor` rappresenta lo stato del terreno di un campo. Osserva la telemetria ambientale, calcola l'evoluzione naturale di umidità e ossigenazione e pubblica il risultato. Quando un attuatore completa un'irrigazione o una riossigenazione, il sensore osserva l'evento e applica l'effetto al proprio stato simulato.

## Responsabilità architetturali

Il servizio **osserva il terreno**. Non deve attivare autonomamente l'Irrigatore. La decisione appartiene al Gestore centrale; l'Irrigatore esegue; il Terrain Sensor applica e conferma l'effetto osservato.

Questa separazione evita che un sensore si comporti anche da attuatore.

## Logica e flusso dati

```text
Ambient Sensor
    ↓ environment/telemetry
Terrain Sensor
    ↓ evoluzione naturale del terreno
terrain/telemetry
    ↓
Gestore centrale
    ↓ comando
Irrigatore
    ↓ terrain/event/irrigated oppure reoxygenated
Terrain Sensor
    ↓ applica l'effetto una volta
terrain/telemetry con ID di conferma
```

Il tipo di suolo iniziale può essere esplicito oppure `random`. Nel caso casuale viene scelto in modo deterministico usando `SOIL_LAYOUT_SEED`, così i tre campi possono avere terreni diversi ma riproducibili tra i riavvii.

## Topic MQTT principali

| Direzione | Topic | Utilizzo |
|---|---|---|
| Sottoscrive | `camp/{field}/environment/telemetry` | Condizioni ambientali |
| Sottoscrive | `camp/{field}/terrain/event/#` | Eventi completati dall'Irrigatore |
| Sottoscrive | `camp/{field}/terrain/cmd/#` | Comandi amministrativi del terreno |
| Pubblica | `camp/{field}/terrain/telemetry` | Stato osservato del terreno |
| Pubblica | `camp/{field}/heartbeat/terrain_sensor` | Presenza del servizio |

Gli eventi di irrigazione e riossigenazione possono contenere un `request_id`. Il sensore riporta l'identificativo nella telemetria di conferma, permettendo al Gestore centrale di chiudere solo la richiesta corretta.


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


Le configurazioni specifiche sono `fields.<field>.terrain.*`, `simulation.soil_layout.*`, `terrain.soil_factors` e `health.publish_interval_seconds`. Gli override storici `FIELD_INIT_TYPE`, `FIELD_INIT_OXY` e `FIELD_INIT_MOIST` sono mantenuti per compatibilità con Docker.

## Struttura del modulo

`soil_type.py` seleziona il terreno iniziale. `soil_moisture.py`, `oxygenation.py` e `irrigation.py` contengono le trasformazioni principali. `terrain_condition.py` compone lo stato e la telemetria. `main.py` gestisce MQTT, deduplicazione degli eventi, heartbeat e riconnessione.

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

Il Compose avvia `terrain_sensor_a`, `terrain_sensor_b` e `terrain_sensor_c`, tutti dalla stessa immagine ma con `FIELD_NAME` diverso.
