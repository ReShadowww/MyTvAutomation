from flask import Flask, render_template, request, make_response, redirect, url_for
import mysql.connector
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

db_config = {
    'host': 'mysql', # <-- Not '127.0.0.1', but the service name (mysql)
    'user': 'localuser',
    'password': 'localpass',
    'database': 'mydb',
    'port': 3306
}

@app.route("/", methods=["GET", "POST"])
def index():
    status = None
    error = None

    # Feedback messages for both buttons
    get_message = request.args.get("get_message")
    get_type = request.args.get("get_type")
    get_id = request.args.get("get_id")
    refresh_message = request.args.get("refresh_message")
    refresh_type = request.args.get("refresh_type")
    refresh_id = request.args.get("refresh_id")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    if request.method == "POST" and 'id' in request.form:
        token_id = request.form.get("id")
        values = (
            request.form.get("client_id", ""),
            request.form.get("client_secret", ""),
            request.form.get("refresh_token", ""),
            request.form.get("access_token", ""),
            request.form.get("device_id", ""),
            request.form.get("auth_code", ""),
            int(request.form.get("auth_code_updated", "0")),
            token_id
        )
        update_query = """
            UPDATE tokens
            SET client_id=%s, client_secret=%s, refresh_token=%s, access_token=%s,
                device_id=%s, auth_code=%s, auth_code_updated=%s
            WHERE id=%s
        """
        try:
            cursor.execute(update_query, values)
            conn.commit()
            status = "success"
        except Exception as e:
            error = str(e)
            status = "fail"

    cursor.execute("SELECT * FROM tokens")
    rows = cursor.fetchall()
    headers = [i[0] for i in cursor.description]
    cursor.close()
    conn.close()

    response = make_response(render_template(
        'tokens.html',
        headers=headers,
        rows=rows,
        status=status,
        error=error,
        get_message=get_message,
        get_type=get_type,
        get_id=get_id,
        refresh_message=refresh_message,
        refresh_type=refresh_type,
        refresh_id=refresh_id
    ))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/get_tokens/<int:token_id>", methods=["POST"])
def get_tokens(token_id):
    message = None
    message_type = None

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT client_id, client_secret, auth_code FROM tokens WHERE id=%s",
            (token_id,)
        )
        row = cursor.fetchone()
        if not row:
            message = f"ID {token_id} not found."
            message_type = "danger"
        else:
            client_id, client_secret, auth_code = row
            url = "https://api.smartthings.com/oauth/token"
            auth = (client_id, client_secret)
            data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": auth_code,
                "redirect_uri": "https://httpbin.org/get"
            }
            try:
                resp = requests.post(url, data=data, auth=auth)
                if resp.status_code == 200:
                    token_data = resp.json()
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
                    cursor.execute(
                        "UPDATE tokens SET access_token=%s, refresh_token=%s WHERE id=%s",
                        (access_token, refresh_token, token_id)
                    )
                    conn.commit()
                    message = f"Tokens obtained for ID {token_id}."
                    message_type = "success"
                else:
                    message = f"Error {resp.status_code}: {resp.text}"
                    message_type = "danger"
            except Exception as e:
                message = f"Exception: {str(e)}"
                message_type = "danger"
        cursor.close()
        conn.close()
    except Exception as e:
        message = f"DB exception: {str(e)}"
        message_type = "danger"

    return redirect(url_for(
        "index",
        get_message=message,
        get_type=message_type,
        get_id=token_id
    ))

@app.route("/refresh_tokens/<int:token_id>", methods=["POST"])
def refresh_tokens(token_id):
    message = None
    message_type = None

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT client_id, client_secret, refresh_token FROM tokens WHERE id=%s",
            (token_id,)
        )
        row = cursor.fetchone()
        if not row:
            message = f"ID {token_id} not found."
            message_type = "danger"
        else:
            client_id, client_secret, refresh_token_val = row
            url = "https://api.smartthings.com/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": refresh_token_val
            }
            try:
                resp = requests.post(
                    url,
                    auth=HTTPBasicAuth(client_id, client_secret),
                    data=data
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    access_token = token_data.get("access_token")
                    new_refresh_token = token_data.get("refresh_token")
                    cursor.execute(
                        "UPDATE tokens SET access_token=%s, refresh_token=%s WHERE id=%s",
                        (access_token, new_refresh_token, token_id)
                    )
                    conn.commit()
                    message = f"Tokens refreshed for ID {token_id}."
                    message_type = "success"
                else:
                    message = f"Error {resp.status_code}: {resp.text}"
                    message_type = "danger"
            except Exception as e:
                message = f"Exception: {str(e)}"
                message_type = "danger"
        cursor.close()
        conn.close()
    except Exception as e:
        message = f"DB exception: {str(e)}"
        message_type = "danger"

    return redirect(url_for(
        "index",
        refresh_message=message,
        refresh_type=message_type,
        refresh_id=token_id
    ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)