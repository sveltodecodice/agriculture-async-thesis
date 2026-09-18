# Harvester

## Scopo

L'`Harvester` è l'attuatore responsabile della raccolta. Riceve una richiesta dal Gestore centrale, registra il raccolto nel deposito persistente, pubblica l'aggiornamento globale e infine emette l'evento che permette alla Plantation Sensor di osservare che il campo è stato raccolto.

## Responsabilità architetturali

Il servizio **esegue e persiste la raccolta**. Il Gestore centrale deve solo decidere e richiedere il raccolto; non deve scrivere direttamente il deposito. Questa separazione evita una doppia registrazione e garantisce che la persistenza avvenga solamente nel componente che rappresenta l'azione completata.

## Logica e flusso dati

```text
Plantation Sensor → READY_FOR_HARVEST
           ↓
Gestore centrale
           ↓ camp/{field}/harvester/cmd/harvest
Harvester
   ├─ salva harvest_deposit.json
   ├─ pubblica camp/harvest_deposit
   └─ pubblica plantation/event/harvested
                    ↓
             Plantation Sensor
                    ↓
                campo vuoto
```

Le tre repliche Harvester condividono la directory `./harvester/data`. Per evitare perdite di dati durante due raccolte contemporanee, `harvester_deposit.py` usa un lock di file POSIX esclusivo durante l'operazione read-modify-write e sostituisce il JSON con una scrittura atomica.

## Topic MQTT principali

| Direzione | Topic | Utilizzo |
|---|---|---|
| Sottoscrive | `camp/{field}/harvester/cmd/harvest` | Richiesta di raccolta |
| Pubblica | `camp/harvest_deposit` | Cronologia globale raccolti |
| Pubblica | `camp/{field}/plantation/event/harvested` | Raccolta completata |
| Pubblica | `camp/{field}/heartbeat/harvester` | Presenza del servizio |


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


Il servizio usa la configurazione MQTT, `FIELD_NAME` e l'intervallo heartbeat. Il percorso del deposito è una costante applicativa sotto `/app/data`, directory persistente montata da Docker.

## Struttura del modulo

`src/core/harvester.py` valida il comando. `src/core/harvester_deposit.py` è l'unico componente che gestisce la persistenza del raccolto. `src/main.py` coordina MQTT, persistenza, evento di completamento e heartbeat.

## Dipendenze

- `aiomqtt`;
- `PyYAML`;
- `pytest`;
- `fcntl` della libreria standard Linux per sincronizzare il file condiviso.


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

Le tre repliche condividono `./harvester/data:/app/data`. Per questo il lock nel modulo di persistenza è necessario anche se ogni container gestisce un solo campo.