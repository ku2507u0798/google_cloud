import pymysql
import qrcode
import io
import base64
import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from fpdf import FPDF

app = Flask(__name__)
CORS(app)

# --- DATABASE CONFIGURATION ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '28032007',
    'cursorclass': pymysql.cursors.DictCursor 
}

def init_db():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS college_events")
    cursor.execute("USE college_events")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100),
            email VARCHAR(100),
            phone VARCHAR(20),
            event_name VARCHAR(100),
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_db_connection():
    return pymysql.connect(**db_config, database='college_events')

# --- 1. REGISTRATION ROUTE ---
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        name = data.get('full_name')
        email = data.get('email')
        phone = data.get('phone')
        event = data.get('event_name')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO participants (full_name, email, phone, event_name) VALUES (%s, %s, %s, %s)", 
            (name, email, phone, event)
        )
        
        # Get the unique ID created for this registration
        reg_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()

        # Generate QR Code including the ID
        qr_content = f"ID: {reg_id} | Name: {name} | Event: {event}"
        qr = qrcode.make(qr_content)
        buffered = io.BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({
            "status": "success",
            "reg_id": reg_id,
            "qr_code": qr_base64,
            "name": name, 
            "email": email, 
            "phone": phone, 
            "event": event
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 2. RECEIPT GENERATION ROUTE ---
@app.route('/download_receipt', methods=['POST'])
def download_receipt():
    try:
        data = request.json
        reg_id = data.get('reg_id', '000')
        name = data.get('name')
        phone = data.get('phone')
        event = data.get('event')
        qr_b64 = data.get('qr_code')

        # Create PDF (Width: 80mm, Height: 165mm)
        pdf = FPDF(format=(80, 165)) 
        pdf.add_page()
        
        # Header - Event Name (Regular Font, Not Bold)
        pdf.set_font("Courier", '', 11) 
        pdf.multi_cell(60, 8, str(event), align='C')
        
        pdf.set_font("Courier", size=7)
        pdf.cell(60, 4, "Karnavati University Campus, Main Hall", ln=True, align='C')
        pdf.cell(60, 4, "Date: 2026-04-03", ln=True, align='C')
        
        pdf.ln(2)
        
        # Table Header
        pdf.set_font("Courier", 'B', 9)
        pdf.cell(30, 8, "Description", align='L')
        pdf.cell(30, 8, "Details", align='R', ln=True)
        
        # Details Section
        pdf.set_font("Courier", size=9)
        
        # Registration ID
        pdf.cell(30, 6, "REGISTRATION ID:", align='L')
        pdf.set_font("Courier", 'B', 9) # Keep ID bold for security
        pdf.cell(30, 6, f"#{reg_id}", align='R', ln=True)
        
        # Participant Name
        pdf.set_font("Courier", '', 9)
        pdf.cell(30, 6, "PARTICIPANT:", align='L')
        pdf.cell(30, 6, f"{name}", align='R', ln=True)
        
        # Phone
        pdf.cell(30, 6, "PHONE:", align='L')
        pdf.cell(30, 6, f"{phone}", align='R', ln=True)
        
        # Event Name in Details (Not Bold, Wrapped)
        pdf.cell(30, 6, "EVENT:", align='L')
        pdf.set_font("Courier", '', 9) 
        pdf.multi_cell(30, 6, f"{event}", align='R')
        
        pdf.ln(2)
        pdf.cell(60, 5, "-" * 35, ln=True, align='C')
        pdf.set_font("Courier", 'B', 9)
        pdf.cell(60, 8, "SCAN FOR ENTRY", ln=True, align='C')

        # QR Code Image Handling
        qr_img_data = base64.b64decode(qr_b64)
        qr_path = f"temp_qr_{reg_id}.png"
        with open(qr_path, "wb") as f:
            f.write(qr_img_data)
        
        pdf.image(qr_path, x=15, y=pdf.get_y() + 2, w=50)
        pdf.ln(52)
        
        # Footer
        pdf.set_font("Courier", 'B', 10)
        pdf.cell(60, 5, "THANK YOU!", ln=True, align='C')
        pdf.set_font("Courier", size=7)
        pdf.cell(60, 5, "Keep this for event entry", ln=True, align='C')

        # Convert PDF to bytes
        pdf_content = pdf.output(dest='S')
        if isinstance(pdf_content, str):
            pdf_content = pdf_content.encode('latin-1')
        pdf_out = io.BytesIO(pdf_content)
        
        # Cleanup temporary image file
        if os.path.exists(qr_path):
            os.remove(qr_path)
        
        return send_file(
            pdf_out, 
            as_attachment=True, 
            download_name=f"Pass_{reg_id}.pdf", 
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 3. ADMIN GET DATA ROUTE ---
@app.route('/get_registrations', methods=['GET'])
def get_registrations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor() 
        cursor.execute("SELECT id, full_name, email, phone, event_name FROM participants ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(port=5000, debug=True)
