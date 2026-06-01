from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import sqlite3
import json

app = Flask(__name__)
CORS(app)

# 配置
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:8b"
CONFIDENCE_THRESHOLD = 0.7
K_DEFAULT = 2
K_HIGH = 5

# 工具函数
def ollama_chat(messages, stream=False):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": messages,
            "stream": stream
        })
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def intent_recognition(q):
    """意图识别：tool_bmi / tool_health_tip / knowledge"""
    prompt = f"""
请识别用户问题意图，只返回：tool_bmi、tool_health_tip、knowledge 三者之一
问题：{q}
    """.strip()
    res = ollama_chat([{"role":"user", "content":prompt}])
    return res.get("message", {}).get("content", "knowledge").strip()

def bmi_calc(weight, height):
    if height <= 0:
        return "身高无效"
    bmi = weight / ((height/100)**2)
    return f"BMI={bmi:.1f}，" + (
        "偏瘦" if bmi<18.5 else
        "正常" if bmi<24 else
        "超重" if bmi<28 else "肥胖"
    )

def health_tip(q):
    res = ollama_chat([{"role":"user", "content":f"给健康建议：{q}"}])
    return res.get("message", {}).get("content", "无建议")

def rag_search(q, k=K_DEFAULT):
    conn = sqlite3.connect("medical_knowledge.db")
    c = conn.cursor()
    c.execute("SELECT answer FROM knowledge WHERE question LIKE ? LIMIT ?", (f"%{q}%", k))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def confidence_estimate(q, ans):
    """简单置信度（0-1）"""
    prompt = f"""
请给回答置信度（0-1，只输出数字）
问题：{q}
回答：{ans}
    """.strip()
    res = ollama_chat([{"role":"user", "content":prompt}])
    try:
        return float(res.get("message", {}).get("content", "0.5"))
    except:
        return 0.5

def save_history(q, a):
    conn = sqlite3.connect("medical_knowledge.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_history(user_q,agent_a) VALUES (?,?)", (q,a))
    conn.commit()
    conn.close()

@app.route("/api/agent", methods=["POST"])
def agent():
    data = request.get_json()
    q = data.get("question", "").strip()
    if not q:
        return jsonify({"error":"问题为空"})

    # 1. 意图识别
    intent = intent_recognition(q)

    # 2. 工具调用
    if intent == "tool_bmi":
        # 简单提取体重身高（示例）
        w, h = 65, 170
        ans = bmi_calc(w, h)
    elif intent == "tool_health_tip":
        ans = health_tip(q)
    else:
        # 3. 动态RAG
        docs = rag_search(q, K_DEFAULT)
        context = "\n".join(docs)
        ans = ollama_chat([
            {"role":"system", "content":"结合知识库回答"},
            {"role":"user", "content":f"知识库：{context}\n问题：{q}"}
        ]).get("message", {}).get("content", "无答案")

        # 4. 置信度+重试
        conf = confidence_estimate(q, ans)
        if conf < CONFIDENCE_THRESHOLD:
            docs = rag_search(q, K_HIGH)
            context = "\n".join(docs)
            ans = ollama_chat([
                {"role":"system", "content":"结合知识库重新回答"},
                {"role":"user", "content":f"知识库：{context}\n问题：{q}"}
            ]).get("message", {}).get("content", "无答案")

    save_history(q, ans)
    return jsonify({"answer": ans})

if __name__ == "__main__":
    app.run(debug=True, port=5000)