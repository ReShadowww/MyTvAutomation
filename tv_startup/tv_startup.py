import requests
from requests.auth import HTTPBasicAuth
import mysql.connector
import time
import sys

# ---- MySQL Config ----
db_config = {
    'host': 'mysql',  # Must match service name in docker-compose.yml
    'user': 'localuser',
    'password': 'localpass',
    'database': 'mydb',
    'port': 3306
}

# --- Utility to get tokens from DB ---
def get_tokens_from_db():
    for i in range(30):  # Try for up to 30 seconds
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT access_token, device_id, client_id, client_secret, refresh_token FROM tokens LIMIT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result and all(result):
                access_token, device_id, client_id, client_secret, refresh_token = result
                return access_token, device_id, client_id, client_secret, refresh_token
            print("❌ No tokens found in database, retrying...")
        except Exception as e:
            print(f"Waiting for MySQL/tokens ({i+1}/30): {e}")
        time.sleep(1)
    print("❌ Could not get tokens from database.")
    sys.exit(1)

# --- Update tokens in DB ---
def set_tokens_in_db(new_access_token, new_refresh_token):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tokens SET access_token=%s, refresh_token=%s WHERE id=1",
            (new_access_token, new_refresh_token)
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database updated with new tokens.")
    except Exception as e:
        print(f"❌ Failed to update tokens in database: {e}")

# --- SmartThingsTV class (unchanged) ---
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

# --- Function to refresh tokens ---
def refresh_tokens(client_id, client_secret, refresh_token):
    url = "https://api.smartthings.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token
    }
    try:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(client_id, client_secret),
            data=data
        )
        if response.status_code == 200:
            token_data = response.json()
            print(
                "Refreshed: Access Token:", token_data["access_token"],
                "\nRefresh Token:", token_data["refresh_token"],
                "\nExpires In:", token_data["expires_in"]
            )
            return token_data["access_token"], token_data["refresh_token"]
        else:
            print("❌ Token refresh failed:", response.status_code)
            print("Response:", response.text)
            return None, None
    except Exception as e:
        print("❌ Exception during token refresh:", e)
        return None, None

# --- Main ---
if __name__ == "__main__":
    print("Getting tokens from MySQL...")
    access_token, device_id, client_id, client_secret, refresh_token = get_tokens_from_db()
    print(f"Using access_token: {access_token[:8]}..., device_id: {device_id}")

    tv = SmartThingsTV(access_token, device_id)
    tv.ensure_on_and_input(target_input="HDMI1", tuner_input="dtv")

    print("Entering hourly refresh loop...")
    while True:
        print("Refreshing tokens from database and SmartThings OAuth...")
        # Always re-load the latest tokens from the DB in case they were updated elsewhere
        _, _, client_id, client_secret, refresh_token = get_tokens_from_db()

        new_access_token, new_refresh_token = refresh_tokens(client_id, client_secret, refresh_token)
        if new_access_token and new_refresh_token:
            set_tokens_in_db(new_access_token, new_refresh_token)
        else:
            print("Keeping old tokens due to refresh failure.")
        time.sleep(3600)  # Wait one hour before next refresh