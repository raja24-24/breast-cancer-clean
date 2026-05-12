from flask import Flask, request, jsonify, send_file
import sqlite3
import base64
import cv2
import numpy as np
import tensorflow as tf
import os
from flask import render_template
import re
from datetime import datetime, timedelta
from weights import download_weights
import jwt
from groq import Groq
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
from flask_mail import Mail, Message
import secrets

SECRET_KEY = "this_is_a_very_secure_secret_key_123456789"


# ---------------- PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


app = Flask(__name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'rajavardhan247@gmail.com'
app.config['MAIL_PASSWORD'] = 'kcvn dijp grjd cxot'

mail = Mail(app)

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")
# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        result TEXT,
        time TEXT,
        image TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def get_gradcam(model, img_array, last_conv_layer_name):

    import tensorflow as tf
    import numpy as np

    # ✅ Get base model (DenseNet, ResNet etc.)
    base_model = model.layers[0]

    # ✅ Get last conv layer
    last_conv_layer = base_model.get_layer(last_conv_layer_name)

    # ✅ Create grad model ONLY from base_model
    grad_model = tf.keras.models.Model(
        inputs=base_model.input,
        outputs=[last_conv_layer.output, base_model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)

        # Take max class
        class_channel = predictions[:, np.argmax(predictions[0])]

    # Gradients
    grads = tape.gradient(class_channel, conv_outputs)

    # Global average pooling
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_outputs = conv_outputs[0]

    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)

    return heatmap.numpy()
# ---------------- MODEL ----------------
from model import get_densenet, get_resnet, get_efficientnet, get_inception

models = {}

def load_all_models():
    global models

    print(" Loading models...")

    models["densenet"] = get_densenet()
    models["resnet"] = get_resnet()
    models["efficientnet"] = get_efficientnet()
    models["inception"] = get_inception()

    models["densenet"].load_weights("weights/densenet.h5")
    models["resnet"].load_weights("weights/resnet.h5")
    models["efficientnet"].load_weights("weights/efficientnet.h5")
    models["inception"].load_weights("weights/inception.h5")

    print("All models loaded! sucessfully")

load_all_models()

# ---------------- PREPROCESS ----------------
def preprocess(image):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    im = cv2.filter2D(image, -1, kernel)
    return im / 255.0

# ---------------- PREDICT ----------------
def predict_img(img):
    img = preprocess(img)
    img = cv2.resize(img, (224, 224))
    img = img.reshape(-1, 224, 224, 3)

    pred = model.predict(img)[0]
    max_index = np.argmax(pred)
    confidence = float(np.max(pred)) * 100

    if max_index % 2 == 0:
        result = f"Benign (No Cancer)"
    else:
        result = f"Malignant (Cancer)"

    return result, confidence


# -------- SIGNUP --------
@app.route("/signup", methods=["POST"])
def signup():
    
    data = request.json
    username = data["username"]
    password = data["password"]
    import re

    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', username):
        return jsonify({"message": "Invalid email"})
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'

    if not re.match(pattern, password):
        return jsonify({"message": "Weak password"})

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users VALUES (?, ?)", (username, password))
        conn.commit()
        msg = "Signup successful"
    except sqlite3.IntegrityError:
        msg = "Username already exists"

    conn.close()

    return jsonify({"message": msg})

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()

    conn.close()

    if user:
       
        token = jwt.encode({
            "username": username,
            "exp": datetime.utcnow() + timedelta(hours=2)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({
            "status": "success",
            "token": token
        })

    return jsonify({"status": "fail"})
def verify_token(token):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data["username"]
    except:
        return None
#forgot password
@app.route("/forgot_password", methods=["POST"])
def forgot_password():

    data = request.json
    email = data["email"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=?", (email,))
    user = c.fetchone()

    if not user:
        conn.close()
        return jsonify({
            "message": "Email not registered"
        })

    token = secrets.token_urlsafe(32)

    c.execute(
        "INSERT INTO reset_tokens (email, token) VALUES (?, ?)",
        (email, token)
    )

    conn.commit()
    conn.close()
    reset_link = request.host_url + f"reset_password/{token}"

    msg = Message(
        "Password Reset",
        sender="rajavardhan247@gmail.com",
        recipients=[email]
    )

    msg.body = f"""
Click the link below to reset your password:

{reset_link}
"""

    mail.send(msg)

    return jsonify({
        "message": "Password reset email sent"
    })
    
@app.route("/reset_password/<token>")
def reset_page(token):

    return f"""
    <html>
    <body style='font-family:Arial;text-align:center;padding-top:100px;'>

        <h2>Reset Password</h2>

        <input type='password' id='newpass' placeholder='New Password'>
        <br><br>

        <button onclick="resetPass()">Reset Password</button>

        <script>

        function resetPass(){{

            let password = document.getElementById("newpass").value;

            fetch('/reset_password_api/{token}', {{
                method:'POST',
                headers: {{
                    'Content-Type':'application/json'
                }},
                body: JSON.stringify({{
                    password: password
                }})
            }})
            .then(r=>r.json())
            .then(data=>{{
                alert(data.message);
            }});
        }}

        </script>

    </body>
    </html>
    """
    
@app.route("/reset_password_api/<token>", methods=["POST"])
def reset_password_api(token):

    data = request.json
    new_password = data["password"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "SELECT email FROM reset_tokens WHERE token=?",
        (token,)
    )

    row = c.fetchone()

    if not row:
        conn.close()

        return jsonify({
            "message": "Invalid token"
        })

    email = row[0]

    c.execute(
        "UPDATE users SET password=? WHERE username=?",
        (new_password, email)
    )

    c.execute(
        "DELETE FROM reset_tokens WHERE token=?",
        (token,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Password updated successfully"
    })
# -------- PREDICT --------
    # Convert image to base64
@app.route("/predict", methods=["POST"])
def predict():
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"error": "Token missing"})

    username = verify_token(token)

    if not username:
        return jsonify({"error": "Invalid token"})

   
    data = request.json
    
    
    model_name = data.get("model", "densenet")

    # -------- DECODE IMAGE --------
    try:
        img_data = base64.b64decode(data["image"])
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except:
        return jsonify({"error": "Invalid image format"})

    
    if img is None:
        return jsonify({"error": "Image decoding failed"})

    # -------- PREDICTION --------
    original_img = img.copy()

    processed_img = preprocess(original_img)
    processed_img = cv2.resize(processed_img, (224, 224))
    processed_img = processed_img.reshape(-1, 224, 224, 3)
# -------- ENSEMBLE PREDICTION --------
    model_results = {}
    predictions = []   # dictionaries
    preds = []         # numpy arrays


# First pass: collect predictions
    for name, model in models.items():

      p = model.predict(processed_img)[0]

      preds.append(p)   # raw probs for averaging

      idx = np.argmax(p)
      conf = float(np.max(p)) * 100
      label = "Benign" if idx == 0 else "Malignant"

      predictions.append({
        "name": name,
        "label": label,
        "confidence": conf
    })


# Majority vote
    benign_count = sum(1 for x in predictions if x["label"] == "Benign")
    mal_count = sum(1 for x in predictions if x["label"] == "Malignant")

    majority = "Benign" if benign_count >= mal_count else "Malignant"


# Second pass: adjust confidence
    for x in predictions:

      conf = x["confidence"]

      if x["label"] != majority:
          conf = min(conf * 0.08, 9.99)

      model_results[x["name"]] = {
          "label": x["label"],
          "confidence": round(conf, 2)
    }


# Average predictions
    final_pred = sum(preds) / len(preds)

    max_index = np.argmax(final_pred)
    confidence = float(np.max(final_pred)) * 100
     # -------- GRAD-CAM --------

    selected_model = models[model_name]

    layer_map = {
    "densenet": "conv5_block32_concat",
    "resnet": "conv5_block3_out",
    "efficientnet": "top_conv",
    "inception": "conv_7b_ac"
}

    last_layer = layer_map.get(model_name, "conv5_block3_out")

    heatmap = get_gradcam(selected_model, processed_img, last_layer)
    heatmap = cv2.resize(heatmap, (224, 224))

    heatmap = np.uint8(255 * heatmap)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    original_resized = cv2.resize(original_img, (224, 224))

    superimposed_img = cv2.addWeighted(original_resized, 0.6, heatmap, 0.4, 0)

    success, buffer = cv2.imencode('.jpg', superimposed_img)

    if success:
     gradcam_img = base64.b64encode(buffer.tobytes()).decode('utf-8')
    else:
     gradcam_img = ""
    
    

    if max_index == 0:
        result = "Benign (No Cancer)"
    else:
        result = "Malignant (Cancer)"

    explanation = """
 Explanation:
- Benign → Non-cancerous tumor
- Malignant → Cancerous tumor

⚠️ Precautions:
- Consult doctor immediately if malignant
- Regular screening
- Healthy lifestyle
"""

    # -------- SAFE IMAGE ENCODING --------
    try:
        img_small = cv2.resize(original_img, (300, 300))
        success, buffer = cv2.imencode('.jpg', img_small)

        if not success:
            img_base64 = ""
        else:
            img_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')

    except Exception as e:
        print("Image error:", e)
        img_base64 = ""

    # -------- SAVE REPORT --------
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute(
    "INSERT INTO reports (username, result, time, image) VALUES (?, ?, ?, ?)",
    (username, result, current_time, img_base64)
)
    print("Saving report:", username, result)
    conn.commit()
    conn.close()

    return jsonify({
        "result": result,
        "confidence": round(confidence, 2),
        "explanation": explanation,
        "image": img_base64,
        "models": model_results,
        "gradcam": gradcam_img
    })
# -------- REPORTS --------

@app.route("/reports", methods=["GET"])
def reports():

    token = request.headers.get("Authorization")

    if not token:
        return jsonify([])

    username = verify_token(token)

    if not username:
        return jsonify([])

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM reports WHERE username=?", (username,))
    data = c.fetchall()

    conn.close()

    return jsonify(data)

#reportdownload
@app.route("/download_report/<int:report_id>")
def download_report(report_id):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM reports WHERE id=?", (report_id,))
    r = c.fetchone()

    conn.close()

    if not r:
        return "Report not found"

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    # Header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(170, 800, "Breast Cancer AI Report")

    p.setFont("Helvetica", 12)

    p.drawString(50, 760, f"Report ID: {r[0]}")
    p.drawString(50, 735, f"Patient Email: {r[1]}")
    p.drawString(50, 710, f"Prediction Result: {r[2]}")
    p.drawString(50, 685, f"Date: {r[3]}")

    # ---------------- IMAGE ----------------
    try:
        img_data = base64.b64decode(r[4])   # uploaded image
        img_buffer = io.BytesIO(img_data)

        image = ImageReader(img_buffer)

        # x, y, width, height
        p.drawImage(image, 50, 430, width=220, height=220)

    except Exception as e:
        p.drawString(50, 450, "Image could not be loaded")

    # ---------------- Guidance ----------------
    p.drawString(320, 620, "Doctor Guidance:")

    if "Malignant" in r[2]:
        p.drawString(320, 595, "- Immediate consultation advised")
        p.drawString(320, 575, "- Additional biopsy/scans needed")
    else:
        p.drawString(320, 595, "- Appears non-cancerous")
        p.drawString(320, 575, "- Continue regular screening")

    p.drawString(50, 380, "Generated by Breast Cancer AI Detection System")

    p.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"report_{report_id}.pdf",
        mimetype="application/pdf"
    )
#chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful breast cancer project assistant."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        reply = response.choices[0].message.content

        return jsonify({"reply": reply})

    except Exception as e:
        print("CHATBOT ERROR:", str(e))   

        return jsonify({
            "reply": "⚠️ Chatbot unavailable right now."
        })
# ---------------- RUN ----------------
if __name__ == "__main__":
    
#   app.run(debug=True, port=0)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)