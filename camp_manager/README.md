# Camp Manager

## Scopo

Il `Camp Manager`, mostrato nella Dashboard come **Gestore centrale**, è il componente decisionale della Smart Farm. Riceve le osservazioni dei sensori, applica le regole automatiche e invia comandi agli attuatori. Coordina inoltre notifiche, stato del sistema e suggerimenti sulle colture.

## Responsabilità architetturali

Il Gestore centrale **decide e orchestra**, ma non modifica direttamente il mondo simulato. Non deve irrigare il terreno, seminare, raccogliere o modificare lo stato della piantagione. Invia invece comandi a Irrigator, Seeder e Harvester e attende le osservazioni successive dei sensori.

Questa è la regola architetturale più importante del progetto:

```text
sensori = osservano
Gestore centrale = decide
attuatori = agiscono
Dashboard = visualizza e invia intenzioni dell'operatore
```

## Logica e flusso dati

Il servizio mantiene uno stato per ciascun campo. Quando riceve telemetria aggiorna il contesto e valuta le policy:

- irrigazione quando l'umidità è sotto la soglia;
- riossigenazione quando l'ossigenazione è troppo bassa;
- raccolta quando la coltura è pronta;
- autosemina dopo il periodo configurato di campo vuoto;
- ranking delle colture per stagione, compatibilità del terreno e distanza dall'umidità minima richiesta.

Per irrigazione e riossigenazione conserva un `request_id` e uno stato `pending`. La richiesta viene chiusa solo quando il Terrain Sensor pubblica una conferma con lo stesso identificativo. Per raccolta e semina il Gestore attende lo stato successivo della Plantation Sensor.

## Topic MQTT principali

### Sottoscrizioni

- `camp/+/environment/telemetry`
- `camp/+/terrain/telemetry`
- `camp/+/plantation/status`
- `camp/+/irrigator/status`
- `camp/+/camp_manager/cmd/#`

### Pubblicazioni

- `camp/{field}/seeder/cmd/plant`
- `camp/{field}/harvester/cmd/harvest`
- `camp/{field}/irrigator/cmd/irrigate`
- `camp/{field}/irrigator/cmd/reoxygenate`
- `camp/{field}/plantation/event/cleared`
- `camp/{field}/system/status`
- `camp/manager/status`
- `camp/notifications`
- `camp/activity_logs`
- `camp/top_seeds`

Il Gestore centrale non pubblica `camp/harvest_deposit`: la persistenza del raccolto appartiene esclusivamente all'Harvester.


## Configurazione

Il servizio legge la configurazione comune da `/app/config/farm.yaml`. Il caricamento è gestito da `src/common/config_loader.py` e segue la stessa precedenza usata dal resto del progetto:

```text
variabile d'ambiente Docker > valore in farm.yaml > valore di default del codice
```

Questa scelta consente di mantenere le proprietà comuni in un solo file e, allo stesso tempo, di modificare un singolo container senza duplicare la configurazione. `FIELD_NAME` identifica la replica associata al campo. La password MQTT è pensata come segreto di runtime e nel Compose deve essere fornita tramite `MQTT_BROKER_PASS`; non viene più salvata con un valore reale nel file YAML del progetto.


Le sezioni principali sono `automation.*`, `health.*`, `farm.fields`, `crops` e la configurazione MQTT. Tra gli override specifici sono disponibili `CAMP_IDS`, `AUTO_SEED_EMPTY_DAYS`, `AUTO_SEED_CHECK_INTERVAL_SECONDS`, `EMPTY_FIELD_MIN_MOISTURE`, `IRRIGATION_TARGET_MARGIN`, `MIN_IRRIGATION_AMOUNT` e `OXYGENATION_THRESHOLD`.

## Catalogo colture e ranking

Il catalogo deriva da `farm.yaml`. Il matcher automatico usa un ordinamento semplice e deterministico:

1. stagione compatibile;
2. terreno ideale compatibile;
3. distanza dall'umidità minima della coltura;
4. nome come spareggio stabile.

La selezione manuale della Dashboard rimane un override dell'operatore e può mostrare anche colture non ideali.

## Persistenza

Il Gestore centrale salva solamente il report giornaliero delle proprie decisioni in `data/daily_farm_log.json`. Non salva il deposito raccolti. Il modulo `orjson` è mantenuto perché viene realmente utilizzato dal report giornaliero.

## Dipendenze

- `aiomqtt`;
- `orjson`;
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

Esiste una sola istanza del Gestore centrale. Il container osserva tutti i campi configurati in `farm.fields`. Il suo heartbeat globale è pubblicato su `camp/manager/status`.
