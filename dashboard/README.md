# Smart Farm Dashboard

Lightweight dashboard implemented with Python standard library, `paho-mqtt`, HTML, CSS, and vanilla JavaScript.

The dashboard has been aligned with the current distributed Smart Farm architecture:

- fields: `field_a`, `field_b`, `field_c` by default;
- one Camp Manager orchestrates all fields;
- Ambient, Terrain, and Plantation services are sensors;
- Seeder, Harvester, and Irrigator are actuators;
- the dashboard sends normal operator actions to Camp Manager rather than bypassing orchestration;
- actuator effects are confirmed through subsequent sensor telemetry.

## Module responsibilities

| File | Responsibility |
|---|---|
| `app.py` | Starts MQTT and HTTP services |
| `config.py` | Broker configuration, configured fields, subscribed topics |
| `state_store.py` | Thread-safe dashboard state |
| `normalizers.py` | Converts sensor payloads into one UI schema |
| `message_handlers.py` | Applies incoming sensor/manager messages to dashboard state |
| `mqtt_contract.py` | Maps operator actions to the system MQTT contract |
| `mqtt_service.py` | MQTT connection, subscriptions, message decoding and publication |
| `http_server.py` | HTTP API, static assets and SSE live state |
| `static/js/pages/home.js` | Farm overview |
| `static/js/pages/field.js` | Field telemetry and operator controls |
| `static/js/pages/diagnostics.js` | MQTT, Camp Manager, sensor health and operator command routing |

## Dashboard data flow

```text
Sensors -> MQTT -> Dashboard MQTT consumer -> normalized state -> HTTP/SSE -> Browser
                  |
                  +-> Camp Manager health

Browser -> HTTP command -> Dashboard MQTT publisher -> Camp Manager -> Actuator
                                                        |
                                                        v
                                                      Sensor
                                                        |
                                                        v
                                                     Telemetry
```

The browser never treats an actuator command as confirmation. The resulting field state remains driven by sensor telemetry.

## Fields

The backend reads the field list from `CAMP_IDS`:

```text
CAMP_IDS=field_a,field_b,field_c
```

If omitted, those three fields are used by default.

The frontend derives its field navigation from the backend snapshot, so field identifiers are not duplicated in JavaScript.

## Operator commands

| UI action | MQTT destination | Logical execution |
|---|---|---|
| Plant | `camp/{field}/camp_manager/cmd/plant` | Camp Manager -> Seeder |
| Irrigate | `camp/{field}/camp_manager/cmd/irrigate` | Camp Manager -> Irrigator |
| Reoxygenate | `camp/{field}/camp_manager/cmd/reoxygenate` | Camp Manager -> Irrigator |
| Clear | `camp/{field}/camp_manager/cmd/clear` | Camp Manager administrative clear event |
| Restart | `camp/{field}/camp_manager/cmd/restart` | Camp Manager state reset |
| Skip days | `camp/{field}/environment/cmd/skip` | Ambient Sensor simulation clock |

`skip` is intentionally an administrative simulation exception: the Ambient Sensor owns the simulated clock.

Harvest is not exposed as a manual dashboard command. When the Plantation Sensor reports `READY_FOR_HARVEST`, Camp Manager automatically commands the Harvester.

## Diagnostics

Camp Manager currently reports health for three sensors per field:

- environment;
- terrain;
- plantation.

Seeder, Harvester, and Irrigator do not currently expose dedicated heartbeat topics, so the dashboard does not invent actuator health. Their successful effects are verified indirectly through Plantation or Terrain telemetry.

## Run

The dashboard service should receive the same MQTT settings used by the rest of the project and the same field list used by Camp Manager.

Example environment:

```yaml
environment:
  - MQTT_BROKER_HOST=mqtt-broker
  - MQTT_BROKER_PORT=8883
  - MQTT_BROKER_USER=farm_admin
  - MQTT_BROKER_PASS=secure_farm
  - CAMP_IDS=field_a,field_b,field_c
```

Rebuild the dashboard from the main project compose file:

```bash
docker compose up -d --build --force-recreate dashboard
```

Open:

```text
http://<docker-host>:8501/
```

Health endpoint:

```text
http://<docker-host>:8501/healthz
```

## Tests

```bash
python -m unittest discover -s tests
```
