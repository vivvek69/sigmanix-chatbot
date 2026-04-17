"""
Database module for Sigmanix Chatbot
Handles all SQLite database operations for students, conversations, feedback, and analysis
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DATABASE_PATH = "chatbot_database.db"


def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Students table - tracks unique visitors and their interest levels
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            visitor_id TEXT PRIMARY KEY UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interest_rating TEXT DEFAULT 'unrated',
            interest_score INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            categories_visited TEXT DEFAULT '[]'
        )
    """)
    
    # Conversations table - logs all user and bot messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL,
            user_message TEXT,
            bot_response TEXT,
            category TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (visitor_id) REFERENCES students(visitor_id)
        )
    """)
    
    # Feedback table - stores user ratings and comments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (visitor_id) REFERENCES students(visitor_id)
        )
    """)
    
    # Student analysis table - stores AI-generated interest analysis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL,
            interest_rating TEXT,
            interest_score INTEGER,
            signals TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (visitor_id) REFERENCES students(visitor_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized at {DATABASE_PATH}")


def get_or_create_student(visitor_id):
    """Get existing student or create new one if not exists"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE visitor_id = ?", (visitor_id,))
    student = cursor.fetchone()
    
    if not student:
        cursor.execute("""
            INSERT INTO students (visitor_id, created_at, last_activity)
            VALUES (?, ?, ?)
        """, (visitor_id, datetime.now(), datetime.now()))
        conn.commit()
        print(f"[OK] New student created: {visitor_id}")
    
    conn.close()
    return student or (visitor_id, datetime.now(), datetime.now(), 'unrated', 0, 0, '[]')


def save_conversation(visitor_id, user_message, bot_response, category=None):
    """Save conversation to database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO conversations (visitor_id, user_message, bot_response, category, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (visitor_id, user_message, bot_response, category, datetime.now()))
    
    # Update student's activity timestamp and message count
    cursor.execute("""
        UPDATE students 
        SET last_activity = ?, message_count = message_count + 1
        WHERE visitor_id = ?
    """, (datetime.now(), visitor_id))
    
    conn.commit()
    conn.close()


def save_feedback(visitor_id, rating, comment=""):
    """Save feedback (rating 1-5) to database"""
    if not (1 <= int(rating) <= 5):
        return {"success": False, "error": "Rating must be between 1 and 5"}
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO feedback (visitor_id, rating, comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (visitor_id, int(rating), comment, datetime.now()))
        
        conn.commit()
        conn.close()
        return {"success": True, "message": "Feedback saved successfully"}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def calculate_student_interest(visitor_id):
    """AI analysis to determine student interest level"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    signals = []
    score = 50  # Start with neutral
    
    # Signal 1: Message count
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE visitor_id = ?", (visitor_id,))
    msg_count = cursor.fetchone()[0]
    if msg_count > 10:
        score += 15
        signals.append(f"High engagement ({msg_count} messages)")
    elif msg_count > 5:
        score += 8
        signals.append(f"Medium engagement ({msg_count} messages)")
    
    # Signal 2: Category diversity
    cursor.execute("SELECT COUNT(DISTINCT category) FROM conversations WHERE visitor_id = ?", (visitor_id,))
    categories_count = cursor.fetchone()[0]
    if categories_count >= 4:
        score += 12
        signals.append(f"Explored {categories_count} categories")
    
    # Signal 3: Feedback rating
    cursor.execute("SELECT AVG(rating) FROM feedback WHERE visitor_id = ?", (visitor_id,))
    result = cursor.fetchone()
    avg_rating = result[0] if result[0] else 0
    if avg_rating >= 4:
        score += 18
        signals.append(f"Positive feedback ({avg_rating:.1f}/5)")
    
    # Normalize score to 0-100
    score = max(0, min(100, score))
    
    # Classify interest level
    if score >= 70:
        rating = "interested"
        emoji = "🟢"
    elif score >= 40:
        rating = "in_doubt"
        emoji = "🟡"
    else:
        rating = "not_interested"
        emoji = "🔴"
    
    conn.close()
    
    return {
        "rating": rating,
        "score": score,
        "signals": signals,
        "emoji": emoji
    }


def save_student_analysis(visitor_id, analysis_data):
    """Save AI analysis results to database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO student_analysis (visitor_id, interest_rating, interest_score, signals, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            visitor_id,
            analysis_data.get('rating'),
            analysis_data.get('score'),
            json.dumps(analysis_data.get('signals', [])),
            datetime.now()
        ))
        
        # Update student's interest rating
        cursor.execute("""
            UPDATE students
            SET interest_rating = ?, interest_score = ?
            WHERE visitor_id = ?
        """, (analysis_data.get('rating'), analysis_data.get('score'), visitor_id))
        
        conn.commit()
        conn.close()
        return {"success": True, "message": "Analysis saved successfully"}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def get_all_students():
    """Get list of all students with their interest levels"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT visitor_id, created_at, last_activity, interest_rating, interest_score, message_count
        FROM students
        ORDER BY last_activity DESC
    """)
    
    students = cursor.fetchall()
    conn.close()
    
    return [{
        "visitor_id": s[0],
        "created_at": s[1],
        "last_activity": s[2],
        "interest_rating": s[3],
        "interest_score": s[4],
        "message_count": s[5]
    } for s in students]


def get_analytics():
    """Get aggregate analytics about all students"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Total students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    
    # Interest distribution
    cursor.execute("""
        SELECT interest_rating, COUNT(*) FROM students
        WHERE interest_rating != 'unrated'
        GROUP BY interest_rating
    """)
    distribution = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Average interest score
    cursor.execute("SELECT AVG(interest_score) FROM students WHERE interest_score > 0")
    avg_score = cursor.fetchone()[0] or 0
    
    # Average feedback rating
    cursor.execute("SELECT AVG(rating) FROM feedback")
    avg_feedback = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "total_students": total_students,
        "interest_distribution": distribution,
        "avg_interest_score": round(avg_score, 2),
        "avg_feedback_rating": round(avg_feedback, 2)
    }
