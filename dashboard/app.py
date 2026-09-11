import json
import os
import queue
import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st

st.set_page_config(
    page_title="Controllo Smart Farm", layout="wide", page_icon="🌱"
)

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

MQTT_QUEUE = queue.Queue()
DEFAULT_DATE = "01/01/2026"

CROPS_INFO = {
    "Pomodoro": {"key": "tomato", "threshold": 0.250, "ideal_soil": "Franco", "days": 60, "water_req": 5.0},
    "Spinaci": {"key": "spinach", "threshold": 0.300, "ideal_soil": "Franco", "days": 40, "water_req": 4.0},
    "Insalata": {"key": "lettuce", "threshold": 0.280, "ideal_soil": "Sabbioso", "days": 30, "water_req": 6.0},
    "Grano": {"key": "wheat", "threshold": 0.180, "ideal_soil": "Argilloso", "days": 90, "water_req": 3.5},
    "Mais": {"key": "corn", "threshold": 0.220, "ideal_soil": "Franco", "days": 75, "water_req": 4.5},
    "Zucchine": {"key": "zucchini", "threshold": 0.260, "ideal_soil": "Franco", "days": 50, "water_req": 5.5},
    "Carote": {"key": "carrot", "threshold": 0.240, "ideal_soil": "Sabbioso", "days": 70, "water_req": 4.0},
    "Patate": {"key": "potato", "threshold": 0.230, "ideal_soil": "Franco", "days": 80, "water_req": 5.0},
}

CROP_KEY_TO_NAME = {
    "tomato": "Pomodoro", "pomodoro": "Pomodoro", "spinach": "Spinaci", "spinaci": "Spinaci",
    "lettuce": "Insalata", "insalata": "Insalata", "wheat": "Grano", "grano": "Grano",
    "corn": "Mais", "mais": "Mais", "zucchini": "Zucchine", "zucchine": "Zucchine",
    "carrot": "Carote", "carote": "Carote", "potato": "Patate", "patate": "Patate",
}

STATUS_BLACKLIST = [
    "too_wet", "too_dry", "healthy", "ok", "clear", "trigger",
    "sospesa", "attiva", "none", "unknown", "vacant", "field is empty",
]

def create_initial_camp_state(crop_name="Pomodoro"):
    return {
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
            "soil_moisture": 0.500,
            "threshold": 0.250,
            "oxygenation": 70.0,
            "soil_type": "Franco",
            "water_dispensed_mm": 0.0,
        },
        "plantation": {
            "crop": crop_name,
            "soil_threshold": CROPS_INFO.get(crop_name, {}).get("threshold", 0.250),
            "harvest_days": CROPS_INFO.get(crop_name, {}).get("days", 60),
            "age_days": 0,
        },
        "history_records": [
            {
                "Data": "01/01",
                "Umidità Suolo (%)": 50.0,
                "Vento (km/h)": 5.0,
                "Radiazione (W/m²)": 150.0,
            }
        ],
    }

def reset_all_campi():
    st.session_state.logs = []
    st.session_state.terrain_types = {"fortnite": "Franco", "campo_2": "Argilloso", "campo_3": "Sabbioso"}
    st.session_state.campi_data = {
        "fortnite": create_initial_camp_state("Pomodoro"),
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

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0: client.subscribe("#")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        MQTT_QUEUE.put((msg.topic, payload))
    except Exception:
        try:
            val = msg.payload.decode()
            MQTT_QUEUE.put((msg.topic, {"value": val}))
        except Exception: pass

@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(ca_certs="/app/certs/ca.crt")
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client

mqtt_client = get_mqtt_client()

def process_mqtt_queue():
    while not MQTT_QUEUE.empty():
        topic, payload = MQTT_QUEUE.get()

        if isinstance(payload, list):
            if len(payload) > 0 and isinstance(payload[0], dict): payload = payload[0]
            else: continue
        if not isinstance(payload, dict): continue

        payload = normalize_payload_keys(payload)
        camp_id = payload.get("camp_id")
        if not camp_id:
            for possible_camp in ["fortnite", "campo_2", "campo_3"]:
                if possible_camp in topic:
                    camp_id = possible_camp
                    break
        if not camp_id: camp_id = "fortnite"
        if camp_id not in st.session_state.campi_data: continue

        target = st.session_state.campi_data[camp_id]
        topic_lower = topic.lower()

        is_ambient = "ambient" in topic_lower or "environment" in topic_lower or "weather" in topic_lower or ("temperature" in payload and "soil_moisture" not in payload)
        if is_ambient:
            target["ambient"].update({k: v for k, v in payload.items() if v is not None})

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
            if "age_days" in payload: target["plantation"]["age_days"] = payload["age_days"]
            if "harvest_days" in payload: target["plantation"]["harvest_days"] = payload["harvest_days"]

        curr_date = target["ambient"].get("short_date") or target["ambient"].get("date", DEFAULT_DATE)[:5]
        curr_m_pct = round(target["terrain"].get("soil_moisture", 0.5) * 100.0, 1)
        curr_w = target["ambient"].get("wind_kmh", 5.0)
        curr_r = target["ambient"].get("radiation_wm2", 150.0)

        history_records = target["history_records"]
        if not history_records or history_records[-1]["Data"] != curr_date:
            history_records.append({"Data": curr_date, "Umidità Suolo (%)": curr_m_pct, "Vento (km/h)": curr_w, "Radiazione (W/m²)": curr_r})
        else:
            history_records[-1].update({"Umidità Suolo (%)": curr_m_pct, "Vento (km/h)": curr_w, "Radiazione (W/m²)": curr_r})

        if len(history_records) > 30: target["history_records"] = history_records[-30:]

        st.session_state.logs.append({
            "Campo": camp_id, "Coltivazione": target["plantation"].get("crop", "N/D"),
            "Terreno": st.session_state.terrain_types.get(camp_id, "Franco"),
            "Data": target["ambient"].get("date", DEFAULT_DATE), "Ora": payload.get("time", "06:00:00"),
            "Evento": topic.split("/")[-1], "Stato": payload.get("status", "OK"),
            "Temp.": f"{target['ambient'].get('temperature', '-')} °C",
            "Umidità aria": f"{target['ambient'].get('humidity_air', '-')} %",
            "Umidità suolo": target["terrain"].get("soil_moisture", "-"),
            "Erogata": f"{payload.get('water_dispensed_mm', 0.0)} mm", "Risparmiata": f"{payload.get('water_saved_mm', 0.0)} mm"
        })
        if len(st.session_state.logs) > 50: st.session_state.logs = st.session_state.logs[-50:]


process_mqtt_queue()

st.sidebar.title("🏞️ Gestione Azienda")
selected_camp = st.sidebar.selectbox("Seleziona Campo da Monitorare", ["fortnite", "campo_2", "campo_3"], index=0)
tab_mon, tab_map, tab_arch = st.tabs(["📊 Monitoraggio", "🗺️ Mappa", "📁 Archivio"])

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
                mqtt_client.publish("environment/cmd/skip", str(skip_val))
                mqtt_client.publish("camp_manager/cmd/skip", str(skip_val))
                st.toast(f"Avanzamento di {skip_val} giorni in corso...")

        with c_irr:
            if st.button("💧 Forza irrigazione", use_container_width=True):
                mqtt_client.publish("terrain/cmd/irrigate", "15.0")
                mqtt_client.publish("camp_manager/cmd/irrigate", "trigger")
                st.toast("Comando irrigazione inviato")

        with c_reox:
            if st.button("💨 Riossigenazione", use_container_width=True):
                mqtt_client.publish("terrain/cmd/reoxygenate", "trigger")
                mqtt_client.publish("camp_manager/cmd/reoxygenate", "trigger")
                st.toast("Riossigenazione terreno inviata (100%)!")

        with c_clear:
            if st.button("🧹 Clear Camp", use_container_width=True):
                mqtt_client.publish("camp_manager/cmd/clear", "trigger")
                st.session_state.campi_data[selected_camp]["plantation"] = {"crop": "Nessuna", "age_days": 0, "harvest_days": 0}
                st.toast("Campo svuotato")

        with c_rst:
            if st.button("🔄 Restart", use_container_width=True):
                reset_all_campi()
                mqtt_client.publish("environment/cmd/reset", "trigger")
                mqtt_client.publish("terrain/cmd/reset", "trigger")
                mqtt_client.publish("camp_manager/cmd/restart", "trigger")
                st.toast("Reset generale completato!")

        with st.expander("🛠️ Semina Nuova Coltivazione & Configurazione Terreno"):
            col_plant, col_soil = st.columns(2)
            with col_plant:
                st.markdown("**🌱 Pianta una nuova coltivazione**")
                chosen_crop_name = st.selectbox("Seleziona Pianta", list(CROPS_INFO.keys()))
                crop_meta = CROPS_INFO[chosen_crop_name]
                st.info(f"💧 **Umidità Preferita**: {crop_meta['threshold']:.3f} ({int(crop_meta['threshold']*100)}%)\n\n⛰️ **Terreno Ideale**: {crop_meta['ideal_soil']}\n\n⏱️ **Tempo Maturazione**: {crop_meta['days']} giorni")
                if st.button("🌱 Conferma Semina"):
                    backend_seed_key = crop_meta["key"]
                    mqtt_client.publish("camp_manager/cmd/plant", backend_seed_key)
                    st.session_state.campi_data[selected_camp]["plantation"] = {"crop": chosen_crop_name, "soil_threshold": crop_meta["threshold"], "harvest_days": crop_meta["days"], "age_days": 0}
                    st.toast(f"Seminato {chosen_crop_name} ({backend_seed_key})!")
            with col_soil:
                st.markdown("**⛰️ Modifica Tipo di Terreno**")
                current_t = st.session_state.terrain_types.get(selected_camp, "Franco")
                new_t = st.selectbox("Tipo di Terreno Corrente", ["Franco", "Argilloso", "Sabbioso"], index=["Franco", "Argilloso", "Sabbioso"].index(current_t))
                if new_t != current_t:
                    st.session_state.terrain_types[selected_camp] = new_t
                    mqtt_client.publish("terrain/cmd/set_soil_type", new_t)
                    st.toast(f"Terreno impostato a {new_t}!")

        st.markdown("---")

        st.markdown("**☁️ Condizioni attuali**")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Temp. Aria", f"{amb.get('temperature', 18.0)} °C")
        m2.metric("Umidità Aria", f"{amb.get('humidity_air', 60.0)} %")
        m3.metric("Pioggia ultima ora", f"{amb.get('rain_mm', 0.0)} mm")
        m4.metric("Vento", f"{amb.get('wind_kmh', 5.0)} km/h")
        m5.metric("Radiazione", f"{amb.get('radiation_wm2', 150.0)} W/m²")

        curr_moisture = ter.get("soil_moisture", 0.500)
        moisture_str = f"{curr_moisture:.3f}" if isinstance(curr_moisture, float) else "--"
        moisture_delta = f"{round(curr_moisture * 100, 1)}% Vol" if isinstance(curr_moisture, float) else "N/D"
        m6.metric("Umidità Suolo", moisture_str, delta=moisture_delta, delta_color="normal")

        st.markdown("---")

        st.markdown("### 🌿 Stato della Pianta e Salute del Suolo")
        crop = plant.get("crop", "Nessuna")
        is_empty = not crop or str(crop).strip().lower() in STATUS_BLACKLIST

        thresh = plant.get("soil_threshold", CROPS_INFO.get(crop, {}).get("threshold", 0.250))
        moisture_loss = ter.get("moisture_loss_today", 0.015)
        oxygenation = ter.get("oxygenation", 70.0)

        if is_empty:
            health_status = "⚪ Campo Vuoto"
            health_desc = "Nessuna coltura attiva"
        elif isinstance(curr_moisture, float):
            if curr_moisture > (thresh + 0.15) or curr_moisture >= 0.70:
                health_status = "🔵 Troppo Umido"
                health_desc = f"Umidità ({round(curr_moisture*100, 1)}%) > Soglia ({round(thresh*100, 1)}%)"
            elif curr_moisture < (thresh - 0.05):
                health_status = "🔴 Troppo Secco"
                health_desc = "Stress idrico critico"
            else:
                health_status = "🟢 In Salute"
                health_desc = "Livello idrico ottimale"
        else:
            health_status = "🟢 In Salute"
            health_desc = "Condizioni stabili"

        age = plant.get("age_days", 0)
        harvest = plant.get("harvest_days", CROPS_INFO.get(crop, {}).get("days", 60))
        days_left = max(0, harvest - age) if not is_empty else 0

        p1, p2, p3, p4, p5, p6 = st.columns(6)
        p1.metric("Coltivazione", crop.capitalize() if not is_empty else "Nessuna")
        p2.metric("Stato di Salute", health_status, delta=health_desc, delta_color="off")
        
        # OSSIGENAZIONE: Freccia giù se non ottimale, colore invertito se critica
        p3.metric(
            "Ossigenazione Suolo", 
            f"{oxygenation:.1f}%", 
            delta="Ottimale (100%)" if oxygenation == 100.0 else "Bassa / Richiesta Riossigenazione", 
            delta_color="normal" if oxygenation >= 50.0 else "inverse"
        )
        
        # UMIDITÀ PERSA: Freccia giù in verde se diminuisce correttamente
        p4.metric(
            "Umidità Persa Oggi", 
            f"-{round(moisture_loss * 100, 1)}%", 
            delta=f"-{moisture_loss:.3f} vol", 
            delta_color="inverse"
        )
        
        # GIORNI AL RACCOLTO: Avanza correttamente in base ai giorni trascorsi (age_days)
        p5.metric(
            "Giorni al Raccolto", 
            f"{days_left} giorni" if not is_empty else "-", 
            delta=f"Maturazione: {int((age / harvest)*100) if (not is_empty and harvest > 0) else 0}%",
            delta_color="off"
        )
        
        p6.metric("Umidità Preferita", f"{thresh:.3f}" if not is_empty else "-", delta=f"{int(thresh * 100)}% Vol" if not is_empty else "-", delta_color="normal")

        st.markdown("---")

        # TABELLA IRRIGAZIONE SENZA "ACQUA NECESSARIA" E CON SPIEGAZIONE SOGLIA SUOLO
        st.markdown("### 🏺 Irrigazione per coltivazione")
        water_req = CROPS_INFO.get(crop.capitalize(), {}).get("water_req", 5.0) if not is_empty else 0.0
        needed = 0.0 if (is_empty or (isinstance(curr_moisture, float) and curr_moisture >= thresh)) else water_req

        df_irr = pd.DataFrame([{
            "Coltivazione": crop.capitalize() if not is_empty else "Nessuna", 
            "Terreno": st.session_state.terrain_types.get(selected_camp, "Franco"),
            "Fabbisogno": f"{water_req} mm", 
            "Soglia suolo (Valore limite ideale, es. 0.3 = 30%)": thresh if not is_empty else "-", 
            "Stato": "🟢 Sospesa" if needed == 0 else "🔴 Attiva"
        }])
        st.dataframe(df_irr, use_container_width=True, hide_index=True)

        st.markdown("### 📋 Parametri d'Intervento Giornalieri")
        water_dispensed = ter.get("water_dispensed_mm", 0.0)
        df_param = pd.DataFrame([{
            "Campo": selected_camp, "Coltivazione": crop.capitalize() if not is_empty else "Nessuna", "Terreno": st.session_state.terrain_types.get(selected_camp, "Franco"),
            "Tipo": "Automatico", "Stato": "Sospesa" if needed == 0 else "Attiva", "Giorno": current_date_str, "Temp. Aria": f"{amb.get('temperature', 18.0)} °C",
            "Umidità Aria": f"{amb.get('humidity_air', 60.0)} %", "Pioggia": f"{amb.get('rain_mm', 0.0)} mm", "Vento": f"{amb.get('wind_kmh', 5.0)} km/h",
            "Radiazione Solare": f"{amb.get('radiation_wm2', 150.0)} W/m²", "Umidità Suolo": moisture_str, "Erogata": f"{water_dispensed} mm", "Risparmiata": f"{water_req - needed} mm"
        }])
        st.dataframe(df_param, use_container_width=True, hide_index=True)

        # 3 GRAFICI SEPARATI
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
        else:
            st.info("In attesa di dati dai sensori...")

        st.markdown("### 📜 Registro cronologico del campo")
        if st.session_state.logs: st.dataframe(pd.DataFrame(st.session_state.logs), use_container_width=True, hide_index=True, height=250)
        else: st.info("Nessun registro ancora salvato...")

    render_live_monitoring()

with tab_map: st.info("Mappa interattiva dei campi.")
with tab_arch: st.info("Archivio dati e report.")