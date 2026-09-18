# Irrigator

## Scopo

L'`Irrigator` è l'attuatore responsabile dell'irrigazione e della riossigenazione del terreno. Riceve richieste dal Gestore centrale, esegue l'azione simulata e pubblica un evento che il Terrain Sensor osserva per aggiornare lo stato fisico simulato.

## Responsabilità architetturali

Il servizio **agisce sul terreno**, ma non decide quando intervenire. Le soglie e le decisioni appartengono al Gestore centrale. Il Terrain Sensor applica l'effetto osservato alla propria telemetria. L'Irrigator mantiene anche uno status periodico che funge da heartbeat e permette alla Dashboard di mostrare l'operazione corrente.

## Logica e flusso dati

```text
Terrain Sensor → telemetria → Gestore centrale
                         ↓ decisione
              Irrigator command
                         ↓
                     Irrigator
                         ↓ evento con request_id
                 Terrain Sensor
                         ↓ conferma
                    telemetria
```

Ogni richiesta può contenere un `request_id`. L'identificativo viene propagato nell'evento di completamento, consentendo al Gestore centrale di collegare comando, attuatore e conferma del sensore senza confondere richieste diverse.

## Topic MQTT principali

| Direzione | Topic | Utilizzo |
|---|---|---|
| Sottoscrive | `camp/{field}/irrigator/cmd/irrigate` | Richiesta irrigazione |
| Sottoscrive | `camp/{field}/irrigator/cmd/reoxygenate` | Richiesta riossigenazione |
| Pubblica | `camp/{field}/terrain/event/irrigated` | Irrigazione completata |
| Pubblica | `camp/{field}/terrain/event/reoxygenated` | Riossigenazione completata |
| Pubblica | `camp/{field}/irrigator/status` | Stato e heartbeat dell'attuatore |


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


I parametri specifici sono `irrigator.status_interval_seconds`, `irrigator.action_delay_seconds` e `irrigator.reoxygenation_target`. Gli override principali sono `IRRIGATOR_STATUS_INTERVAL`, `IRRIGATOR_ACTION_DELAY` e `REOXYGENATION_TARGET`.

## Struttura del modulo

`src/core/irrigator.py` valida e normalizza le operazioni. `src/main.py` mantiene lo stato dell'attuatore, pubblica lo status e gestisce i due comandi MQTT.

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

Una replica viene avviata per ciascun campo. A differenza degli altri servizi con heartbeat dedicato, lo status periodico dell'Irrigator è già sufficiente per determinare disponibilità e operazione corrente.
