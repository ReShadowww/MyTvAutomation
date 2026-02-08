import requests
import mysql.connector
import time
import sys

# ---- MySQL Config ----
db_config = {
    'host': 'mysql',            # Must match service name in docker-compose.yml
    'user': 'localuser',
    'password': 'localpass',
    'database': 'mydb',
    'port': 3306
}

def get_tokens_from_db():
    for i in range(30):  # Try for up to 30 seconds
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT access_token, device_id FROM tokens LIMIT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result and result[0] and result[1]:
                return result[0], result[1]
            print("❌ No tokens found in database, retrying...")
        except Exception as e:
            print(f"Waiting for MySQL/tokens ({i+1}/30): {e}")
        time.sleep(1)
    print("❌ Could not get tokens from database.")
    sys.exit(1)

# ---- SmartThingsTV class ----
class SmartThingsTV:
    def __init__(self, token, device_id, check_interval=3, max_wait_power=30, max_wait_input=20):
        self.token = token
        self.device_id = device_id
        self.check_interval = check_interval
        self.max_wait_power = max_wait_power
        self.max_wait_input = max_wait_input
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        self.status_url = f"https://api.smartthings.com/v1/devices/{self.device_id}/status"
        self.command_url = f"https://api.smartthings.com/v1/devices/{self.device_id}/commands"

    def get_status(self):
        resp = requests.get(self.status_url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        power = data["components"]["main"]["switch"]["switch"]["value"]
        try:
            input_src = data["components"]["main"]["samsungvd.mediaInputSource"]["inputSource"]["value"]
        except KeyError:
            input_src = None
        return power, input_src

    def send_command(self, component, capability, command, arguments=None):
        payload = {"commands": [{
            "component": component,
            "capability": capability,
            "command": command,
            "arguments": arguments or []
        }]}
        resp = requests.post(self.command_url, headers=self.headers, json=payload, timeout=10)
        resp.raise_for_status()
        return resp

    def ensure_on_and_input(self, target_input="HDMI1", tuner_input="dtv"):
        power, current_input = self.get_status()
        if power != "on":
            print("TV is off. Turning it on...")
            self.send_command("main", "switch", "on")
            elapsed = 0
            while elapsed < self.max_wait_power:
                time.sleep(self.check_interval)
                elapsed += self.check_interval
                power, _= self.get_status()
                if power == "on":
                    print(f"TV is now ON after {elapsed} seconds.")
                    break
            else:
                print(f"⚠️ TV did not turn on after {self.max_wait_power} seconds.")
                return
        else:
            print("TV is already ON.")

        _, current_input = self.get_status()
        if current_input == tuner_input:
            print(f"TV input is {tuner_input}. Switching to {target_input}...")
            self.send_command("main", "samsungvd.mediaInputSource", "setInputSource", [target_input])
            elapsed = 0
            while elapsed < self.max_wait_input:
                time.sleep(self.check_interval)
                elapsed += self.check_interval
                _, current_input = self.get_status()
                if current_input == target_input:
                    print(f"✅ Input switched to {target_input} after {elapsed} seconds.")
                    break
            else:
                print(f"⚠️ Input did not switch to {target_input} after {self.max_wait_input} seconds.")
        else:
            print(f"TV input is already {target_input}. No change needed.")

# ---- Main ----

if __name__ == "__main__":
    print("Getting tokens from MySQL...")
    access_token, device_id = get_tokens_from_db()
    print(f"Using access_token: {access_token[:8]}..., device_id: {device_id}")

    tv = SmartThingsTV(access_token, device_id)
    tv.ensure_on_and_input(target_input="HDMI1", tuner_input="dtv")