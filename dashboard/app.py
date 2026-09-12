from datetime import datetime
import json
import os
import queue
import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st

# Importazione centralizzata dei semi da seeds.py
try:
    from seeds import CROPS_INFO, CROP_KEY_TO_NAME
except ImportError:
    try:
        from camp_manager.seeds import CROPS_INFO, CROP_KEY_TO_NAME
    except ImportError:
        # Fallback locale di sicurezza
        CROPS_INFO = {
            "Pomodoro": {"key": "tomato", "threshold": 0.250, "ideal_soil": "Franco", "days": 60},
            "Grano": {"key": "wheat", "threshold": 0.180, "ideal_soil": "Argilloso", "days": 90},
            "Insalata": {"key": "lettuce", "threshold": 0.280, "ideal_soil": "Sabbioso", "days": 30},
        }
        CROP_KEY_TO_NAME = {"tomato": "Pomodoro", "wheat": "Grano", "lettuce": "Insalata"}

st.set_page_config(
    page_title="Controllo Smart Farm", layout="wide", page_icon="🌱"
)

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

DEFAULT_DATE = "01/01/2026"

STATUS_BLACKLIST = [
    "too_wet", "too_dry", "healthy", "ok", "clear", "trigger",
    "sospesa", "attiva", "none", "unknown", "vacant", "field is empty", "nessuna"
]

NOISY_TOPICS = ["status_detail", "plant_name", "health", "status", "cmd"]
SPECIAL_EVENTS = ["RACCOLTO COMPLETATO", "AUTO_IRRIGATE", "AUTO_PLANT", "AUTO_OXYGENATE"]

SOIL_TYPES_OPTIONS = ["Franco", "Argilloso", "Sabbioso", "Franco-Sabbioso", "Franco-Argilloso"]

if "harvest_deposit" not in st.session_state:
    st.session_state.harvest_deposit = []

if "logs" not in st.session_state:
    st.session_state.logs = []


@st.cache_resource
def get_mqtt_service():
    msg_queue = queue.Queue()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe("camp/#")
            client.subscribe("#")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            msg_queue.put((msg.topic, payload))
        except Exception:
            try:
                val = msg.payload.decode()
                msg_queue.put((msg.topic, {"value": val}))
            except Exception:
                pass

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(ca_certs="/app/certs/ca.crt")
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    return client, msg_queue


mqtt_client, MQTT_QUEUE = get_mqtt_service()


def create_initial_camp_state(crop_name="Pomodoro"):
    crop_meta = CROPS_INFO.get(crop_name, {"threshold": 0.250, "days": 60})
    return {
        "current_day_tracker": DEFAULT_DATE,
        "ambient": {
            "date": DEFAULT_DATE,
            "short_date": "01/01",
            "season": "Inverno",
            "weather": "Sereno",
            "temperature": 18.0,
            "humidity_air": 60.0,
            "rain_mm": 0.0,
            "wind_kmh": 5.0,
            "radiation_wm2": 150.0,
        },
        "terrain": {
            "soil_moisture": 0.280,
            "threshold": crop_meta.get("threshold", 0.250),
            "oxygenation": 70.0,
            "soil_type": "Franco",
            "water_dispensed_mm": 0.0,
        },
        "plantation": {
            "crop": crop_name,
            "soil_threshold": crop_meta.get("threshold", 0.250),
            "harvest_days": crop_meta.get("days", 60),
            "age_days": 0,
            "planted_date": DEFAULT_DATE,
        },
        "history_records": [
            {
                "Data": "01/01",
                "Umidità Suolo (%)": 28.0,
                "Vento (km/h)": 5.0,
                "Radiazione (W/m²)": 150.0,
            }
        ],
    }


def reset_all_campi():
    st.session_state.logs = []
    st.session_state.harvest_deposit = []
    st.session_state.terrain_types = {"campo_1": "Franco", "campo_2": "Argilloso", "campo_3": "Sabbioso"}
    st.session_state.campi_data = {
        "campo_1": create_initial_camp_state("Pomodoro"),
        "campo_2": create_initial_camp_state("Grano"),
        "campo_3": create_initial_camp_state("Insalata"),
    }


if "campi_data" not in st.session_state:
    reset_all_campi()


def normalize_payload_keys(d):
    if not isinstance(d, dict): return d
    norm = {}
    for k, v in d.items():
        k_low = str(k).lower()
        if k_low in ["temperature", "temp", "temp_aria"]: norm["temperature"] = v
        elif k_low in ["humidity_air", "humidity", "air_humidity"]: norm["humidity_air"] = v
        elif k_low in ["rain_mm", "rain", "pioggia"]: norm["rain_mm"] = v
        elif k_low in ["wind_kmh", "wind", "vento"]: norm["wind_kmh"] = v
        elif k_low in ["radiation_wm2", "radiation", "radiazione"]: norm["radiation_wm2"] = v
        elif k_low in ["soil_moisture", "moisture", "umidita_suolo"]: norm["soil_moisture"] = v
        elif k_low in ["oxygenation", "ossigenazione", "oxygen"]: norm["oxygenation"] = v
        elif k_low in ["water_dispensed_mm", "water_applied_mm", "erogata"]: norm["water_dispensed_mm"] = v
        else: norm[k] = v

    if "day" in d and "month" in d and "year" in d:
        try:
            norm["date"] = f"{int(d['day']):02d}/{int(d['month']):02d}/{int(d['year'])}"
            norm["short_date"] = f"{int(d['day']):02d}/{int(d['month']):02d}"
        except (ValueError, TypeError): pass
    return norm


def process_mqtt_queue():
    while not MQTT_QUEUE.empty():
        topic, payload = MQTT_QUEUE.get()

        if isinstance(payload, list):
            if len(payload) > 0 and isinstance(payload[0], dict): payload = payload[0]
            else: continue
        if not isinstance(payload, dict): continue

        payload = normalize_payload_keys(payload)
        
        parts = topic.split("/")
        camp_id = parts[1] if (len(parts) >= 2 and parts[0] == "camp") else payload.get("camp_id")

        if camp_id == "fortnite":
            camp_id = "campo_1"

        if not camp_id or camp_id not in st.session_state.campi_data:
            for possible_camp in ["campo_1", "campo_2", "campo_3"]:
                if possible_camp in topic:
                    camp_id = possible_camp
                    break

        if not camp_id or camp_id not in st.session_state.campi_data:
            continue

        target = st.session_state.campi_data[camp_id]
        topic_lower = topic.lower()
        event_name = topic.split("/")[-1]

        is_ambient = "ambient" in topic_lower or "environment" in topic_lower or "weather" in topic_lower or ("temperature" in payload and "soil_moisture" not in payload)
        if is_ambient:
            target["ambient"].update({k: v for k, v in payload.items() if v is not None})
            
            w_curr = str(target["ambient"].get("weather", "")).lower()
            if w_curr in ["rain", "rainy", "pioggia"] and float(target["ambient"].get("rain_mm", 0.0)) == 0.0:
                target["ambient"]["rain_mm"] = 5.0

            new_date = target["ambient"].get("date", DEFAULT_DATE)
            old_date = target.get("current_day_tracker", DEFAULT_DATE)

            if old_date and new_date != old_date:
                try:
                    d_old = datetime.strptime(old_date, "%d/%m/%Y")
                    d_new = datetime.strptime(new_date, "%d/%m/%Y")
                    delta_days = (d_new - d_old).days
                except ValueError:
                    delta_days = 1

                if delta_days > 0:
                    target["current_day_tracker"] = new_date
                    plant = target["plantation"]
                    crop_name = plant.get("crop", "Nessuna")
                    is_empty = not crop_name or str(crop_name).strip().lower() in STATUS_BLACKLIST

                    if not is_empty:
                        plant["age_days"] = plant.get("age_days", 0) + delta_days
                        harvest_days = plant.get("harvest_days", 60)

                        if plant["age_days"] >= harvest_days:
                            st.session_state.harvest_deposit.append({
                                "Campo": camp_id.upper(),
                                "Coltivazione": crop_name,
                                "Data Piantagione": plant.get("planted_date", DEFAULT_DATE),
                                "Data Raccolta": new_date,
                                "Giorni Impiegati": harvest_days,
                                "Stato Finale": "🌾 Raccolto con Successo"
                            })

                            st.session_state.logs.append({
                                "Campo": camp_id,
                                "Coltivazione": crop_name,
                                "Terreno": st.session_state.terrain_types.get(camp_id, "Franco"),
                                "Data": new_date,
                                "Ora": "12:00:00",
                                "Evento": "RACCOLTO COMPLETATO",
                                "Stato": "Raccolto",
                                "Temp.": f"{target['ambient'].get('temperature', '-')} °C",
                                "Umidità aria": f"{target['ambient'].get('humidity_air', '-')} %",
                                "Umidità suolo": target["terrain"].get("soil_moisture", "-"),
                                "Erogata": f"{target['terrain'].get('water_dispensed_mm', 0.0)} mm",
                                "Risparmiata": "0.0 mm"
                            })
                            
                            target["plantation"] = {
                                "crop": "Nessuna",
                                "soil_threshold": 0.250,
                                "harvest_days": 0,
                                "age_days": 0,
                                "planted_date": "-"
                            }
                            mqtt_client.publish(f"camp/{camp_id}/camp_manager/cmd/clear", "trigger")

        is_terrain = "terrain" in topic_lower or "soil" in topic_lower or "soil_moisture" in payload
        if is_terrain:
            payload.pop("date", None)
            payload.pop("short_date", None)
            target["terrain"].update({k: v for k, v in payload.items() if v is not None})
            if "soil_moisture" in payload and payload["soil_moisture"] is not None:
                try:
                    sm_float = float(payload["soil_moisture"])
                    if sm_float > 1.0: sm_float = sm_float / 100.0
                    target["terrain"]["soil_moisture"] = sm_float
                except ValueError: pass

        is_plant = "plantation" in topic_lower or "plant" in topic_lower or "crop" in topic_lower
        if is_plant:
            raw_crop = str(payload.get("crop", payload.get("plant", payload.get("value", "")))).lower()
            if raw_crop and raw_crop not in STATUS_BLACKLIST:
                mapped_crop = CROP_KEY_TO_NAME.get(raw_crop)
                if mapped_crop:
                    target["plantation"]["crop"] = mapped_crop
                    target["plantation"]["soil_threshold"] = CROPS_INFO[mapped_crop]["threshold"]
                    target["plantation"]["harvest_days"] = CROPS_INFO[mapped_crop]["days"]

        curr_date = target["ambient"].get("short_date") or target["ambient"].get("date", DEFAULT_DATE)[:5]
        curr_m_pct = round(target["terrain"].get("soil_moisture", 0.28) * 100.0, 1)
        curr_w = target["ambient"].get("wind_kmh", 5.0)
        curr_r = target["ambient"].get("radiation_wm2", 150.0)

        history_records = target["history_records"]
        if not history_records or history_records[-1]["Data"] != curr_date:
            history_records.append({"Data": curr_date, "Umidità Suolo (%)": curr_m_pct, "Vento (km/h)": curr_w, "Radiazione (W/m²)": curr_r})
        else:
            history_records[-1].update({"Umidità Suolo (%)": curr_m_pct, "Vento (km/h)": curr_w, "Radiazione (W/m²)": curr_r})

        if len(history_records) > 30: target["history_records"] = history_records[-30:]

        if event_name not in NOISY_TOPICS:
            curr_full_date = target["ambient"].get("date", DEFAULT_DATE)
            already_logged_today = any(
                l.get("Campo") == camp_id and l.get("Data") == curr_full_date
                for l in st.session_state.logs
            )

            if not already_logged_today or event_name in SPECIAL_EVENTS:
                real_status = payload.get("status") or payload.get("health") or payload.get("state")
                if not real_status or str(real_status).lower() in STATUS_BLACKLIST:
                    sm = target["terrain"].get("soil_moisture", 0.28)
                    th = target["plantation"].get("soil_threshold", 0.25)
                    real_status = "Troppo Secco" if sm < th else ("Troppo Umido" if sm > (th + 0.05) else "In Salute")

                st.session_state.logs.append({
                    "Campo": camp_id, 
                    "Coltivazione": target["plantation"].get("crop", "N/D"),
                    "Terreno": st.session_state.terrain_types.get(camp_id, "Franco"),
                    "Data": curr_full_date, 
                    "Ora": payload.get("time", "06:00:00"),
                    "Evento": event_name.upper() if event_name not in NOISY_TOPICS else "TELEMETRIA", 
                    "Stato": str(real_status).capitalize(),
                    "Temp.": f"{target['ambient'].get('temperature', '-')} °C",
                    "Umidità aria": f"{target['ambient'].get('humidity_air', '-')} %",
                    "Umidità suolo": f"{target['terrain'].get('soil_moisture', 0.28):.3f}",
                    "Erogata": f"{payload.get('water_dispensed_mm', 0.0)} mm", 
                    "Risparmiata": f"{payload.get('water_saved_mm', 0.0)} mm"
                })
                if len(st.session_state.logs) > 300: 
                    st.session_state.logs = st.session_state.logs[-300:]


st.sidebar.title("🏞️ Gestione Azienda")
selected_camp = st.sidebar.selectbox("Seleziona Campo da Monitorare", ["campo_1", "campo_2", "campo_3"], index=0)

tab_mon, tab_arch = st.tabs(["📊 Monitoraggio", "📁 Archivio"])

with tab_mon:
    @st.fragment(run_every="2s")
    def render_live_monitoring():
        process_mqtt_queue()
        camp_info = st.session_state.campi_data[selected_camp]
        amb = camp_info["ambient"]
        ter = camp_info["terrain"]
        plant = camp_info["plantation"]

        current_date_str = amb.get("date", DEFAULT_DATE)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("📅 Data (G/M/Y)", current_date_str)
        kpi2.metric("🍂 Stagione", str(amb.get("season", "Inverno")).capitalize())
        kpi3.metric("☀️ Meteo", str(amb.get("weather", "Sereno")).capitalize())
        kpi4.metric("⛰️ Tipo di Terreno", st.session_state.terrain_types.get(selected_camp, "Franco"))

        st.markdown("---")
        st.subheader(f"🪴 Campo Attuale: {selected_camp.upper()}")

        c_skip, c_irr, c_reox, c_clear, c_rst = st.columns([2, 1.5, 1.5, 1.5, 1.5])
        with c_skip:
            skip_val = st.number_input("Avanza giorni", min_value=1, max_value=30, value=1, label_visibility="collapsed")
            if st.button("⏩ Skip Days"):
                mqtt_client.publish(f"camp/{selected_camp}/environment/cmd/skip", str(skip_val))
                st.toast(f"Avanzamento di {skip_val} giorni inviato a {selected_camp.upper()}!")

        with c_irr:
            if st.button("💧 Forza irrigazione", use_container_width=True):
                # Invia unicamente al camp_manager che gestisce l'istruzione verso il terreno
                mqtt_client.publish(f"camp/{selected_camp}/camp_manager/cmd/irrigate", "trigger")
                st.toast(f"Comando irrigazione inviato a {selected_camp.upper()}")

        with c_reox:
            if st.button("💨 Riossigenazione", use_container_width=True):
                # Invia unicamente al camp_manager
                mqtt_client.publish(f"camp/{selected_camp}/camp_manager/cmd/reoxygenate", "trigger")
                st.toast(f"Riossigenazione inviata a {selected_camp.upper()}!")

        with c_clear:
            if st.button("🧹 Clear Camp", use_container_width=True):
                mqtt_client.publish(f"camp/{selected_camp}/camp_manager/cmd/clear", "trigger")
                st.session_state.campi_data[selected_camp]["plantation"] = {"crop": "Nessuna", "age_days": 0, "harvest_days": 0, "planted_date": "-"}
                st.toast(f"Campo {selected_camp.upper()} svuotato")

        with c_rst:
            if st.button("🔄 Restart", use_container_width=True):
                st.session_state.campi_data[selected_camp] = create_initial_camp_state("Pomodoro")
                st.session_state.terrain_types[selected_camp] = "Franco"
                st.session_state.logs = [l for l in st.session_state.logs if l.get("Campo") != selected_camp]

                mqtt_client.publish(f"camp/{selected_camp}/environment/cmd/reset", DEFAULT_DATE)
                mqtt_client.publish(f"camp/{selected_camp}/terrain/cmd/reset", "trigger")
                mqtt_client.publish(f"camp/{selected_camp}/camp_manager/cmd/restart", "trigger")
                st.toast(f"Reset completato per il campo {selected_camp.upper()} al {DEFAULT_DATE}!")

        with st.expander("🛠️ Semina Nuova Coltivazione & Configurazione Terreno"):
            col_plant, col_soil = st.columns(2)
            with col_plant:
                st.markdown("**🌱 Pianta una nuova coltivazione**")
                chosen_crop_name = st.selectbox("Seleziona Pianta", list(CROPS_INFO.keys()))
                crop_meta = CROPS_INFO[chosen_crop_name]
                
                min_req = crop_meta['threshold']
                max_req = crop_meta.get('max_threshold', min_req + 0.050)
                st.info(
                    f"💧 **Umidità Preferita / Range Ideale**: {min_req:.3f} - {max_req:.3f} ({int(min_req*100)}% - {int(max_req*100)}%)\n\n"
                    f"⛰️ **Terreno Ideale**: {crop_meta.get('ideal_soil', 'Franco')}\n\n"
                    f"⏱️ **Tempo Maturazione**: {crop_meta.get('days', 60)} giorni"
                )
                if st.button("🌱 Conferma Semina"):
                    backend_seed_key = crop_meta["key"]
                    mqtt_client.publish(f"camp/{selected_camp}/camp_manager/cmd/plant", backend_seed_key)
                    st.session_state.campi_data[selected_camp]["plantation"] = {
                        "crop": chosen_crop_name, 
                        "soil_threshold": crop_meta["threshold"], 
                        "harvest_days": crop_meta["days"], 
                        "age_days": 0,
                        "planted_date": current_date_str
                    }
                    st.toast(f"Seminato {chosen_crop_name} su {selected_camp.upper()}!")
            with col_soil:
                st.markdown("**⛰️ Modifica Tipo di Terreno**")
                current_t = st.session_state.terrain_types.get(selected_camp, "Franco")
                if current_t not in SOIL_TYPES_OPTIONS:
                    current_t = "Franco"
                new_t = st.selectbox("Tipo di Terreno Corrente", SOIL_TYPES_OPTIONS, index=SOIL_TYPES_OPTIONS.index(current_t))
                if new_t != current_t:
                    st.session_state.terrain_types[selected_camp] = new_t
                    mqtt_client.publish(f"camp/{selected_camp}/terrain/cmd/set_soil_type", new_t)
                    st.toast(f"Terreno di {selected_camp.upper()} impostato a {new_t}!")

        st.markdown("---")

        st.markdown("**☁️ Condizioni attuali**")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Temp. Aria", f"{amb.get('temperature', 18.0)} °C")
        m2.metric("Umidità Aria", f"{amb.get('humidity_air', 60.0)} %")
        m3.metric("Pioggia ultima ora", f"{amb.get('rain_mm', 0.0)} mm")
        m4.metric("Vento", f"{amb.get('wind_kmh', 5.0)} km/h")
        m5.metric("Radiazione", f"{amb.get('radiation_wm2', 150.0)} W/m²")

        curr_moisture = ter.get("soil_moisture", 0.280)
        moisture_str = f"{curr_moisture:.3f}" if isinstance(curr_moisture, float) else "--"
        moisture_delta = f"{round(curr_moisture * 100, 1)}% Vol" if isinstance(curr_moisture, float) else "N/D"
        m6.metric("Umidità Suolo", moisture_str, delta=moisture_delta, delta_color="normal")

        st.markdown("---")

        st.markdown("### 🌿 Stato della Pianta e Salute del Suolo")
        crop = plant.get("crop", "Nessuna")
        is_empty = not crop or str(crop).strip().lower() in STATUS_BLACKLIST

        min_thresh = plant.get("soil_threshold", CROPS_INFO.get(crop, {}).get("threshold", 0.250))
        max_thresh = min_thresh + 0.050
        
        moisture_loss = ter.get("moisture_loss_today", 0.020)
        oxygenation = ter.get("oxygenation", 70.0)

        if is_empty:
            health_status = "⚪ Campo Vuoto"
            health_desc = "Nessuna coltura attiva"
        elif isinstance(curr_moisture, float):
            if curr_moisture < min_thresh:
                health_status = "🔴 Troppo Secco"
                health_desc = f"Umidità ({curr_moisture:.3f}) < Min ({min_thresh:.3f})"
            elif curr_moisture > max_thresh:
                health_status = "🔵 Troppo Umido"
                health_desc = f"Umidità ({curr_moisture:.3f}) > Max ({max_thresh:.3f})"
            else:
                health_status = "🟢 In Salute"
                health_desc = f"Livello idrico ottimale ({min_thresh:.3f} - {max_thresh:.3f})"
        else:
            health_status = "🟢 In Salute"
            health_desc = "Condizioni stabili"

        age = plant.get("age_days", 0)
        harvest = plant.get("harvest_days", CROPS_INFO.get(crop, {}).get("days", 60))
        days_left = max(0, harvest - age) if not is_empty else 0

        p1, p2, p3, p4, p5, p6 = st.columns(6)
        p1.metric("Coltivazione", crop.capitalize() if not is_empty else "Nessuna")
        p2.metric("Stato di Salute", health_status, delta=health_desc, delta_color="off")
        
        p3.metric(
            "Ossigenazione Suolo", 
            f"{oxygenation:.1f}%", 
            delta="Ottimale (100%)" if oxygenation == 100.0 else "Richiesta Riossigenazione", 
            delta_color="normal" if oxygenation >= 50.0 else "inverse"
        )
        
        p4.metric(
            "Umidità Persa Oggi", 
            f"-{round(moisture_loss * 100, 1)}%", 
            delta=f"-{moisture_loss:.3f} vol", 
            delta_color="inverse"
        )
        
        p5.metric(
            "Giorni al Raccolto", 
            f"{days_left} giorni" if not is_empty else "-", 
            delta=f"Maturazione: {int((age / harvest)*100) if (not is_empty and harvest > 0) else 0}%",
            delta_color="off"
        )
        
        p6.metric(
            "Range Ideale", 
            f"{min_thresh:.3f} - {max_thresh:.3f}" if not is_empty else "-", 
            delta=f"{int(min_thresh*100)}% - {int(max_thresh*100)}% Vol" if not is_empty else "-", 
            delta_color="normal"
        )

        st.markdown("---")

        # CALCOLO BILANCIO IDRICO DINAMICO
        rain_mm = float(amb.get("rain_mm", 0.0))
        if is_empty or not isinstance(curr_moisture, float):
            fabbisogno_mm = 0.0
            erogata_mm = 0.0
            risparmiata_mm = 0.0
            stato_irr = "🟢 Sospesa"
        else:
            target_moisture = min_thresh + 0.050
            fabbisogno_raw = max(0.0, (target_moisture - curr_moisture) * 100.0)
            fabbisogno_mm = round(fabbisogno_raw, 1)

            erogata_raw = max(0.0, fabbisogno_mm - rain_mm)
            erogata_mm = round(erogata_raw, 1)

            if curr_moisture >= min_thresh or rain_mm >= fabbisogno_mm:
                stato_irr = "🟢 Sospesa"
                risparmiata_mm = round(rain_mm if rain_mm > 0 else fabbisogno_mm, 1)
            else:
                stato_irr = "🔴 Attiva"
                risparmiata_mm = round(rain_mm, 1)

        st.markdown("### 🏺 Irrigazione per coltivazione")
        df_irr = pd.DataFrame([{
            "Coltivazione": crop.capitalize() if not is_empty else "Nessuna", 
            "Terreno": st.session_state.terrain_types.get(selected_camp, "Franco"),
            "Fabbisogno Teorico": f"{fabbisogno_mm} mm", 
            "Soglia min suolo": min_thresh if not is_empty else "-", 
            "Stato Impianto": stato_irr
        }])
        st.dataframe(df_irr, use_container_width=True, hide_index=True)

        st.markdown("### 📋 Parametri d'Intervento Giornalieri")
        # COLONNA RINOMINATA IN "Irrigazione" E PIOGGIA CONFLUITA IN "Risparmiata"
        df_param = pd.DataFrame([{
            "Campo": selected_camp, 
            "Coltivazione": crop.capitalize() if not is_empty else "Nessuna", 
            "Terreno": st.session_state.terrain_types.get(selected_camp, "Franco"),
            "Tipo": "Automatico", 
            "Irrigazione": stato_irr, 
            "Giorno": current_date_str, 
            "Temp. Aria": f"{amb.get('temperature', 18.0)} °C",
            "Umidità Aria": f"{amb.get('humidity_air', 60.0)} %", 
            "Vento": f"{amb.get('wind_kmh', 5.0)} km/h",
            "Radiazione Solare": f"{amb.get('radiation_wm2', 150.0)} W/m²", 
            "Umidità Suolo": moisture_str, 
            "Erogata": f"{erogata_mm} mm", 
            "Risparmiata": f"{risparmiata_mm} mm"
        }])
        st.dataframe(df_param, use_container_width=True, hide_index=True)

        st.markdown("### 📈 Andamento Parametri")
        history_records = camp_info.get("history_records", [])
        if history_records:
            df_hist = pd.DataFrame(history_records)
            st.markdown("💧 **Umidità del Suolo (%)**")
            st.line_chart(df_hist, x="Data", y="Umidità Suolo (%)", height=200)

            st.markdown("💨 **Vento (km/h)**")
            st.line_chart(df_hist, x="Data", y="Vento (km/h)", height=200)

            st.markdown("☀️ **Radiazione Solare (W/m²)**")
            st.line_chart(df_hist, x="Data", y="Radiazione (W/m²)", height=200)

        st.markdown("### 📜 Registro cronologico del campo attivo")
        camp_logs = [l for l in st.session_state.logs if l.get("Campo") == selected_camp]
        if camp_logs:
            st.dataframe(pd.DataFrame(camp_logs), use_container_width=True, hide_index=True, height=250)
        else:
            st.info(f"Nessun registro salvato per il campo {selected_camp.upper()}...")

    render_live_monitoring()

with tab_arch:
    st.title("📁 Archivio Dati e Registro Globale")
    
    st.markdown("### 📦 Deposito e Registro Storico Raccolti Generale")
    if st.session_state.harvest_deposit:
        st.dataframe(pd.DataFrame(st.session_state.harvest_deposit), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun raccolto stoccato nel deposito generale.")

    st.markdown("---")
    st.markdown("### 📜 Registri Cronologici di Tutti i Campi")

    c1, c2, c3 = st.columns(3)
    c_list = ["campo_1", "campo_2", "campo_3"]
    cols = [c1, c2, c3]

    for idx, c_id in enumerate(c_list):
        with cols[idx]:
            st.subheader(f"🏟️ Registro: {c_id.upper()}")
            logs_c = [l for l in st.session_state.logs if l.get("Campo") == c_id]
            if logs_c:
                st.dataframe(pd.DataFrame(logs_c), use_container_width=True, hide_index=True, height=400)
            else:
                st.info(f"Nessun registro per {c_id.upper()}")