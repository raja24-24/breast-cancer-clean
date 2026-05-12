from flask import Flask, request, jsonify
import sqlite3
from model_loader import load_model, predict_img
import base64
import cv2
import numpy as np

app = Flask(__name__)
model = load_model()

# -------- DATABASE --------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS reports (username TEXT, result TEXT, time TEXT)")
    conn.commit()
    conn.close()

init_db()

# -------- AUTH --------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO users VALUES (?, ?)", (data["username"], data["password"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Signup success"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", 
              (data["username"], data["password"]))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

# -------- PREDICT --------
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    username = data["username"]

    # Decode image
    img_data = base64.b64decode(data["image"])
    np_arr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    result = predict_img(img)

    explanation = """
Benign: Non-cancerous  
Malignant: Cancerous  

Precautions:
- Consult doctor immediately  
- Regular screening  
- Healthy lifestyle  
"""

    # Save report
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO reports VALUES (?, ?, datetime('now'))", 
              (username, result))
    conn.commit()
    conn.close()

    return jsonify({
        "result": result,
        "explanation": explanation
    })

# -------- REPORTS --------
@app.route("/reports/<username>", methods=["GET"])
def reports(username):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE username=?", (username,))
    data = c.fetchall()
    conn.close()

    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)