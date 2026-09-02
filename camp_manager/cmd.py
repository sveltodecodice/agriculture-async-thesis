import sys
import paho.mqtt.publish as publish

if len(sys.argv) < 2:
    print("Use: python cmd.py [plant <name> | irrigate | clear | skip <days>]")
    sys.exit(1)

action = sys.argv[1].lower()
broker = "localhost"

if action == "plant":
    choose_seed = sys.argv[2] if len(sys.argv) > 2 else "tomato"
    publish.single("camp_manager/cmd/plant", choose_seed, hostname=broker)
    print(f"-> Sent command: Plant {choose_seed}")
elif action == "irrigate":
    publish.single("camp_manager/cmd/irrigate", "trigger", hostname=broker)
    print("-> Sent command: Force Irrigation")
elif action == "clear":
    publish.single("camp_manager/cmd/clear", "trigger", hostname=broker)
    print("-> Sent command: Clear Camp")
elif action == "skip":
    days = sys.argv[2] if len(sys.argv) > 2 else "1"
    publish.single("camp_manager/cmd/skip", days, hostname=broker)
    print(f"-> Sent command: Skip {days} days")
else:
    print("Unknown command.")