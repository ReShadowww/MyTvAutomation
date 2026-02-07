from flask import Flask, render_template, request, make_response
import mysql.connector

app = Flask(__name__)

db_config = {
    'host': 'mysql',       # <-- Not '127.0.0.1', but the service name (mysql)
    'user': 'localuser',
    'password': 'localpass',
    'database': 'mydb',
    'port': 3306
}

@app.route("/", methods=["GET", "POST"])
def index():
    status = None
    error = None

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    if request.method == "POST":
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

    response = make_response(render_template('tokens.html',
                                             headers=headers,
                                             rows=rows,
                                             status=status,
                                             error=error))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)