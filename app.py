import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
app = Flask(__name__)
CORS(app)

# --- 1. CLOUD DATABASE CONNECTION ---
mongo_client = MongoClient(os.environ.get("MONGO_URI"))
db = mongo_client["edubloom_db"]
papers_col = db["papers"]

# --- 2. AI BRAIN CONNECTION ---
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/')
def home():
    return jsonify({"status": "Online", "database": "Connected", "ai": "Ready"})

# --- DATABASE ROUTE: Save Papers ---
@app.route('/api/papers', methods=['GET', 'POST'])
def handle_papers():
    if request.method == 'POST':
        paper_data = request.json
        papers_col.insert_one(paper_data)
        return jsonify({"status": "success", "message": "Saved to MongoDB!"})
    elif request.method == 'GET':
        all_papers = list(papers_col.find({}, {"_id": 0}))
        return jsonify(all_papers)

# --- AI ROUTE: Exam Generator ---
@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get("prompt")
    
    sys_msg = "You are an API that outputs ONLY raw, valid JSON arrays. Do not include markdown block quotes like ```json. Just the raw array."
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt}
        ]
    )
    
    output = response.choices[0].message.content.strip()
    
    # Safety net to clean up AI markdown formatting
    if output.startswith("```json"):
        output = output[7:-3].strip()
    elif output.startswith("```"):
        output = output[3:-3].strip()
        
    try:
        questions = json.loads(output)
    except Exception as e:
        print("JSON Error:", output)
        questions = []
        
    return jsonify({"questions": questions})

# --- AI ROUTE: Chatbot ---
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")
        print(f"📥 Received from frontend: {user_msg}")

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant. Keep answers brief."},
                {"role": "user", "content": user_msg}
            ]
        )

        reply = response.choices[0].message.content
        print(f"📤 AI Reply generated successfully!")
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return jsonify({"reply": "Backend crashed!"}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)