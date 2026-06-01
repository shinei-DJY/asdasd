import sqlite3

def init_db():
    conn = sqlite3.connect("medical_knowledge.db")
    c = conn.cursor()
    # 医疗知识库
    c.execute('''
    CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT
    )
    ''')
    # 对话历史
    c.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_q TEXT,
        agent_a TEXT
    )
    ''')
    # 插入示例数据
    sample = [
        ("感冒症状", "发热、咳嗽、流涕、咽痛、乏力"),
        ("高血压饮食", "低盐低脂、多蔬菜水果、少烟酒"),
        ("糖尿病运动", "每周≥150分钟中等强度运动，如快走、游泳")
    ]
    c.executemany("INSERT OR IGNORE INTO knowledge(question,answer) VALUES (?,?)", sample)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")