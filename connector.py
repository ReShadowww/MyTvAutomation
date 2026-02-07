from flask import Flask, render_template_string, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

db_config = {
    'host': '127.0.0.1',
    'user': 'localuser',
    'password': 'localpass',
    'database': 'mydb',
    'port': 3306
}

@app.route("/", methods=["GET", "POST"])
def index():
    status = request.args.get("status")
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
            token_id
        )
        update_query = """
            UPDATE tokens
            SET client_id=%s, client_secret=%s, refresh_token=%s, access_token=%s,
                device_id=%s, auth_code=%s
            WHERE id=%s
        """
        try:
            cursor.execute(update_query, values)
            conn.commit()
            cursor.close()
            conn.close()
            # Redirect after POST, include status parameter
            return redirect(url_for('index', status='success'))
        except Exception as e:
            print(e)
            cursor.close()
            conn.close()
            return redirect(url_for('index', status='fail'))

    cursor.execute("SELECT * FROM tokens")
    rows = cursor.fetchall()
    headers = [i[0] for i in cursor.description]
    cursor.close()
    conn.close()

    template = '''
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Tokens Database</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #f8fafc; }
            .table-responsive { margin-top: 40px; }
            h2 { margin-top: 40px; margin-bottom: 20px; }
            input[type="text"] { min-width: 120px; }
            @media (max-width: 600px) {
                h2 { font-size: 1.3rem; }
                .table th, .table td { font-size: 0.92rem; }
                input[type="text"] { min-width: 60px; }
            }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Tokens Table - Edit Data</h2>
          {% if status == 'success' %}
            <div class="alert alert-success" role="alert">
              Update successful!
            </div>
          {% elif status == 'fail' %}
            <div class="alert alert-danger" role="alert">
              Update failed. Please try again.
            </div>
          {% endif %}
          <div class="table-responsive">
            <table class="table table-striped table-bordered align-middle">
                <thead class="table-dark">
                    <tr>
                    {% for header in headers %}
                        <th>{{ header }}</th>
                    {% endfor %}
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                {% for row in rows %}
                <tr>
                    <form method="post">
                    {% for i in range(headers|length) %}
                        {% if headers[i] == "id" %}
                            <td>
                                <input type="hidden" name="id" value="{{ row[i] }}">
                                <span class="fw-bold">{{ row[i] }}</span>
                            </td>
                        {% else %}
                            <td>
                                <input type="text" class="form-control" name="{{ headers[i] }}" value="{{ row[i] }}">
                            </td>
                        {% endif %}
                    {% endfor %}
                        <td>
                            <button type="submit" class="btn btn-primary btn-sm">Update</button>
                        </td>
                    </form>
                </tr>
                {% endfor %}
                </tbody>
            </table>
          </div>
        </div>
      </body>
    </html>
    '''
    return render_template_string(template, headers=headers, rows=rows, status=status)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)