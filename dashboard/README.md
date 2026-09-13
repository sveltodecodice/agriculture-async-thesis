# Smart Farm Dashboard — student-friendly edition

A lightweight dashboard written with **Python standard library + paho-mqtt + HTML/CSS/vanilla JS**.
There is no frontend framework and no Flask/FastAPI dependency.

## Why the code is split this way

Each module has one job:

| File | Responsibility |
|---|---|
| `app.py` | starts the application |
| `config.py` | ports, broker settings, topics, camp IDs |
| `state_store.py` | shared thread-safe state |
| `normalizers.py` | converts MQTT payloads into one predictable schema |
| `message_handlers.py` | routes incoming MQTT messages into state |
| `mqtt_contract.py` | maps UI actions to MQTT commands |
| `mqtt_service.py` | connects/subscribes/publishes to MQTT |
| `http_server.py` | HTTP API, static files, live SSE stream |
| `static/js/pages/*` | one frontend module per page |
| `static/css/*` | design tokens, layout, reusable components |

The intended data flow is:

```text
Sensors -> MQTT -> Camp Manager -> MQTT
                      |             |
                      +-- health ---+
                                    v
                              mqtt_service.py
                                    v
                           message_handlers.py
                                    v
                             state_store.py
                                    v
                         HTTP/SSE -> Browser UI
```

## Pages

- **Panoramica**: current date, MQTT/manager connectivity, fields, short review.
- **Field detail**: crop state, telemetry and supported commands.
- **Diagnostica**: Camp Manager sensor health (`environment`, `terrain`, `plantation`).

## Supported UI commands

- irrigate
- reoxygenate
- plant
- clear
- restart
- skip days

The action-to-topic mapping is isolated in `mqtt_contract.py`.

## Run

The existing compose file can keep the dashboard service on port `8501`.

```bash
docker compose up -d --build --force-recreate dashboard_app
```

Health check:

```bash
curl http://localhost:8501/healthz
```

## Run the small parser test

From the dashboard directory:

```bash
python -m unittest discover -s tests
```

## Good first student extensions

1. Add a chart page without changing MQTT handling.
2. Add a crop attribute in `seeds.py` and display it in `pages/field.js`.
3. Add a new command only in `mqtt_contract.py`, then expose one button.
4. Add an archive persistence module without touching the live MQTT service.
