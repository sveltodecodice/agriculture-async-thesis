import sys
import paho.mqtt.publish as publish

if len(sys.argv) < 2:
    print("Use: python cmd.py [plant <name> | irrigate | clear | skip <days> | reoxygenate | reset]")
    sys.exit(1)

action = sys.argv[1].lower()
broker = "localhost"
auth_config = {"username": "farm_admin", "password": "secure_farm"}

if action == "plant":
    choose_seed = sys.argv[2] if len(sys.argv) > 2 else "tomato"
    publish.single("camp_manager/cmd/plant", choose_seed.lower(), hostname=broker, auth=auth_config)
    print(f"-> Sent command: Plant {choose_seed}")
elif action == "irrigate":
    publish.single("camp_manager/cmd/irrigate", "trigger", hostname=broker, auth=auth_config)
    print("-> Sent command: Force Irrigation")
elif action == "clear":
    publish.single("camp_manager/cmd/clear", "trigger", hostname=broker, auth=auth_config)
    print("-> Sent command: Clear Camp")
elif action == "skip":
    days = sys.argv[2] if len(sys.argv) > 2 else "1"
    publish.single("camp_manager/cmd/skip", days, hostname=broker, auth=auth_config)
    print(f"-> Sent command: Skip {days} day(s)")
elif action == "reoxygenate":
    publish.single("camp_manager/cmd/reoxygenate", "trigger", hostname=broker, auth=auth_config)
    print("-> Sent command: Reoxygenate Soil")
elif action == "reset":
    publish.single("camp_manager/cmd/reset", "trigger", hostname=broker, auth=auth_config)
    print("-> Sent command: RESET")
else:
    print("Unknown command.")