import asyncio
import json
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import aiomqtt

from core.telemetry_handler import live_state, handle_telemetry_message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

async def run_mqtt_listener():
    while True:
        try:
            async with aiomqtt.Client(hostname=MQTT_HOST, port=MQTT_PORT) as client:
                await client.subscribe("environment/telemetry")
                await client.subscribe("camp/terrain_telemetry")
                await client.subscribe("plantation/status")
                
                async for message in client.messages:
                    await handle_telemetry_message(str(message.topic), json.loads(message.payload.decode()))
        except Exception:
            await asyncio.sleep(3)

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_mqtt_listener())
    print("Access it locally at: http://localhost:8080")

@app.get("/")
def serve_ui():
    return FileResponse("dashboard.html")

@app.get("/api/dashboard-data")
def get_dashboard_data():
    return live_state

@app.get("/api/semi")
def get_seeds():
    return {"semi": [{"nome": s["name"], "label": s["name"].capitalize()} for s in list_seeds]}

@app.post("/api/comandi/avanza-giorni")
async def skip_days(request: Request):
    body = await request.json()
    giorni = int(body.get("giorni", 1))
    async with aiomqtt.Client(hostname=MQTT_HOST, port=MQTT_PORT) as client:
        await client.publish("environment/skip_day", str(giorni))
    return {"status": "ok"}

@app.post("/api/comandi/pianta-seme")
async def plant_seed(request: Request):
    body = await request.json()
    nome = str(body.get("nome", ""))
    async with aiomqtt.Client(hostname=MQTT_HOST, port=MQTT_PORT) as client:
        await client.publish("camp_manager/cmd/plant", nome)
    return {"status": "ok"}