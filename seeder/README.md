# Seeder

## Scopo

Il `Seeder` è l'attuatore responsabile dell'esecuzione della semina. Riceve una richiesta dal Gestore centrale e, dopo averla validata, pubblica l'evento che indica alla Plantation Sensor che la semina è avvenuta.

## Responsabilità architetturali

Il servizio **agisce**, ma non decide. Non sceglie la coltura e non verifica autonomamente quale seme sia migliore: queste responsabilità appartengono al Gestore centrale e al seed matcher. Il Seeder deve limitarsi a normalizzare ed eseguire la richiesta ricevuta.

## Logica e flusso dati

```text
Dashboard / automazione
        ↓ intento
Gestore centrale
        ↓ camp/{field}/seeder/cmd/plant
Seeder
        ↓ esecuzione
camp/{field}/plantation/event/seeded
        ↓
Plantation Sensor
        ↓
plantation/status
```

Il comando rappresenta una richiesta; l'evento `seeded` rappresenta l'azione eseguita. Questa distinzione è importante perché il sensore non deve modificare la piantagione solo perché è stato pubblicato un comando.

## Topic MQTT principali

| Direzione | Topic | Utilizzo |
|---|---|---|
| Sottoscrive | `camp/{field}/seeder/cmd/plant` | Richiesta di semina |
| Pubblica | `camp/{field}/plantation/event/seeded` | Conferma dell'esecuzione |
| Pubblica | `camp/{field}/heartbeat/seeder` | Presenza del servizio |


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


Il Seeder usa soprattutto la configurazione MQTT, `FIELD_NAME` e `health.publish_interval_seconds`. Non possiede parametri agronomici propri perché non effettua ranking delle colture.

## Struttura del modulo

`src/core/seeder.py` contiene la piccola logica di validazione e normalizzazione del comando. `src/main.py` gestisce il ciclo MQTT, l'heartbeat e la riconnessione.

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

Il Compose crea una replica per ogni campo. Il nome del container cambia, mentre il codice e l'immagine rimangono gli stessi.
