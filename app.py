"""
iot-web-application

Author: Vlad Cojocaru (https://github.com/vladcojocaru)
Copyright (c) 2025
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timezone
from lib.controller import ET_7017, ET_7052
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import bcrypt
import pymysql
from pymysql.cursors import DictCursor
import requests
import xml.etree.ElementTree as ET

valori_senzori = {
    "temperatura": None,
    "temperaturaProcesor": None,
    "tensiune": None,
    "uptime": None,
    "curentTime": None,
    "out0": None,
    "ET7017": None,
    "ET7052": None
}

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

print("Calea absolută către .env:", env_path.resolve())
print(".env există?", env_path.exists())
print("DB_HOST =", os.getenv("DB_HOST"))

with open("config/test.json", "r") as f:
    config = json.load(f)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_key_in_caz_ca_lipsește")

login_manager = LoginManager()
login_manager.init_app(app)

def build_url(ctrl_cfg, path=""):
    schema = ctrl_cfg.get("schema", "http")
    host = ctrl_cfg["host"]
    port = ctrl_cfg["port"]
    return f"{schema}://{host}:{port}{path}"

valori_primite = []

def get_mysql_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=DictCursor
        )

class User(UserMixin):
    def __init__(self, id, first_name, email, role_id):
        self.id = id
        self.first_name = first_name
        self.email = email
        self.role_id = role_id

@login_manager.user_loader
def load_user(user_id):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, email, role_id FROM tbl_user WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], first_name=user_data['first_name'], email=user_data['email'], role_id=user_data['role_id'])
    return None

lan_ctrl_cfg = config["controllers"]["lan_controller"]

LAN_CONTROLLER_URL = build_url(lan_ctrl_cfg, lan_ctrl_cfg.get("status_path", ""))
controller17 = ET_7017(config["controllers"]["ET-7017"]["host"], config["controllers"]["ET-7017"]["port"])
controller52 = ET_7052(config["controllers"]["ET-7052"]["host"], config["controllers"]["ET-7052"]["port"])
digital_output = int(config["controllers"]["digital_output"])
digital_input = int(config["controllers"]["digital_input"])
output_ON = build_url(lan_ctrl_cfg, lan_ctrl_cfg.get("out_on_path", ""))
output_OFF = build_url(lan_ctrl_cfg, lan_ctrl_cfg.get("out_off_path", ""))

@app.route('/')
@login_required
def index():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.permission FROM tbl_role_permission rp
        JOIN tbl_permission p ON rp.permission_id = p.id
        WHERE rp.role_id = %s
    """, (current_user.role_id,))
    permissions = [row['permission'] for row in cursor.fetchall()]
    conn.close()
    return render_template("index.html", permissions=permissions, user = current_user)

@app.route('/valori')
@login_required
def lista_valori():
    return render_template("valori.html", valori=valori_primite, user = current_user)

@app.route('/grafic')
@login_required
def grafic():
    return render_template("grafic.html",  user = current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tbl_user WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            password_hash = user_data['password'].encode('utf-8')

            if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                user = User(id=user_data['id'], first_name=user_data['first_name'], email=user_data['email'], role_id=user_data['role_id'])
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Email sau parola gresita')
                return redirect(url_for('login'))
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/update')
def updateAll():
    api_key = request.args.get('api_key')
    field1_raw = request.args.get('DS1')

    if not field1_raw:
        return jsonify({"error": "DS1 lipseste"}), 400

    try:
        field1 = round(float(field1_raw), 1)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO valori (senzor, valoare, timestamp) VALUES (%s, %s, %s)",
                       ("DS1", field1, timestamp))
        conn.commit()
        conn.close()

        return jsonify({"status": "ok", "valoare": field1, "timestamp": timestamp}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/valori_json')
def valori_json():

    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT senzor, valoare, timestamp FROM valori ORDER BY id DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()

    rezultate = []

    for row in rows:
        
        dt_naive = row['timestamp']
        dt_utc = dt_naive.replace(tzinfo=timezone.utc)  
        iso_utc = dt_utc.isoformat()  

        rezultate.append({
            "senzor": row['senzor'],
            "valoare": row['valoare'],
            "timestamp": iso_utc  
        })

    return jsonify(rezultate)

@app.route('/api/valori_grafic')
def valori_grafic():
    start = request.args.get('start')
    end = request.args.get('end')

    if not start or not end or start.lower() == 'null' or end.lower() == 'null':
        return jsonify({"error": "Parametrii 'start' și 'end' sunt obligatorii și nu pot fi 'null'."}), 400

    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, valoare FROM valori WHERE timestamp BETWEEN %s AND %s ORDER BY timestamp ASC", (start, end))
    rows = cursor.fetchall()
    conn.close()

    data = []
    for r in rows:
        dt_naive = r['timestamp']
        dt_utc = dt_naive.replace(tzinfo=timezone.utc)  # UTC
        iso_utc = dt_utc.isoformat()
        data.append({"timestamp": iso_utc, "valoare": float(r['valoare'])})

    return jsonify(data)
@app.route('/api/temperatura')
def temperatura():
    try:
        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_temp = root.find("ds1").text
        temperatura = round(int(raw_temp) / 10.0, 1)
        valori_senzori["temperatura"] = temperatura
        return jsonify({"temperatura": temperatura})
    except Exception as e:
        print("Eroare:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/temperaturaProcesor')
def temperaturaProcesor():
    try:
        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_tempProc = root.find("tem").text
        temperaturaProcesor = round(int(raw_tempProc) / 100.0, 1)
        valori_senzori["temperaturaProcesor"] = temperaturaProcesor
        return jsonify({"temperaturaProcesor": temperaturaProcesor})
    except Exception as e:
        print("Eroare:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/tensiune')
def tensiune():
    try:
        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_ten = root.find("vin").text
        tensiune = round(int(raw_ten) / 100.00, 2)
        valori_senzori["tensiune"] = tensiune
        return jsonify({"tensiune": tensiune})
    except Exception as e:
        print("Eroare:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/uptime')
def uptime():
    try:
        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        zile = root.find("sec3").text
        ore = root.find("sec2").text
        min = root.find("sec1").text
        sec = root.find("sec0").text
        uptime = f"{zile} zile {ore} ore {min} minute {sec} secunde"
        valori_senzori["uptime"] = uptime
        return jsonify({"uptime": uptime})
    except Exception as e:
        print("Eroare:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/curenttime')
def curenttime():
    try:
        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_data_ora = root.find("sec4").text
        

        utc_time = datetime.fromtimestamp(int(raw_data_ora), tz=timezone.utc)
        valori_senzori["curentTime"] = utc_time.strftime("%Y-%m-%d %H:%M:%S")
        return jsonify({"data_ora": utc_time.strftime("%Y-%m-%d %H:%M:%S")})
    except Exception as e:
        print("Eroare:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_out0')
def get_out0():
    try:
        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_out0= root.find("out0").text
        out0 = int(raw_out0)
        valori_senzori["out0"] = out0
        return jsonify({"out0": out0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/set_out0_on', methods=['POST'])
def set_out0_on():
    try:
        requests.get(output_ON, timeout=3)

        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_out0= root.find("out0").text
        out0 = int(raw_out0)

        return jsonify({"out0": out0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/set_out0_off', methods=['POST'])
def set_out0_off():
    try:
        requests.get(output_OFF, timeout=3)

        response = requests.get(LAN_CONTROLLER_URL, timeout=3)
        root = ET.fromstring(response.content)
        raw_out0= root.find("out0").text
        out0 = int(raw_out0)

        return jsonify({"out0": out0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/ET7017')
def et7017():
    try:
        inputs = controller17.read_analog_inputs(0,digital_input)
        inputs = round(int(inputs[0]) / 1000.0, 3)
        valori_senzori["ET7017"] = inputs
        return jsonify({"inputs": inputs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_ET7052')
def get_ET7052():
    try:
        inputs = controller52.read_digital_outputs(0,2)
        valori_senzori["ET7052"] = inputs
        return jsonify({"inputs": inputs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ET7052_ON', methods=['POST'])
def et7052_ON():
    try:
        controller52.set_output(digital_output, 1)
        return jsonify({"success": True, "output": digital_output, "status": 1})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ET7052_OFF', methods=['POST'])
def et7052_OFF():
    try:
        controller52.set_output(digital_output, 0)
        return jsonify({"success": True, "output": digital_output, "status": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/valori_senzori')
def valori_senzori_api():
    temperatura()
    temperaturaProcesor()
    tensiune()
    uptime()
    curenttime()
    get_out0()
    et7017()
    get_ET7052()
    return jsonify(valori_senzori)

if __name__ == '__main__':
    app.run("0.0.0.0", port= 5000, debug=True)
