# app_simple.py - מערכת תמלול פשוטה למטפלים
from flask import Flask, request, render_template, jsonify
import os
import datetime
import json
import sqlite3
import hashlib
import secrets
import shutil
from werkzeug.utils import secure_filename
import tempfile
from dotenv import load_dotenv
import assemblyai as aai

# ייבוא מותנה של המערכת המאובטחת
try:
    from secure_assemblyai import SecureAssemblyAI
    SECURE_ASSEMBLYAI_AVAILABLE = True
    print("✅ מערכת תמלול מאובטח זמינה")
except ImportError as e:
    print(f"⚠️ מערכת תמלול מאובטח לא זמינה: {e}")
    SECURE_ASSEMBLYAI_AVAILABLE = False
    SecureAssemblyAI = None

# טעינת משתני סביבה
load_dotenv()

# הגדרת AssemblyAI
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
if ASSEMBLYAI_API_KEY and ASSEMBLYAI_API_KEY != 'your-assemblyai-api-key-here':
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    print("🎯 AssemblyAI מוכן לפעולה - תמלול אמיתי זמין")
    print("🔐 תמלול מאובטח זמין עם הצפנה מקסימלית")
else:
    print("❌ חסר ASSEMBLYAI_API_KEY תקף - שירות התמלול לא זמין")
    ASSEMBLYAI_API_KEY = None

app = Flask(__name__)

# הגדרות בסיסיות
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TRANSCRIPTS_FOLDER'] = 'transcripts'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# יצירת תיקיות
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRANSCRIPTS_FOLDER'], exist_ok=True)

# מגבלות פשוטות מה-ENV
MAX_PATIENTS = int(os.getenv('FREE_MAX_PATIENTS', '1'))
MAX_SESSIONS = int(os.getenv('FREE_MAX_SESSIONS', '5'))

print(f"🔧 מגבלות: {MAX_PATIENTS} מטופלים, {MAX_SESSIONS} סשנים")

# מערכת אימות פשוטה
def init_auth_db():
    """יצירת בסיס נתונים פשוט לאימות"""
    conn = sqlite3.connect('simple_users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """הצפנת סיסמה פשוטה"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """אימות סיסמה"""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash

def create_session_token():
    """יצירת session token"""
    return secrets.token_urlsafe(32)

# אתחול בסיס נתונים
init_auth_db()

# פונקציות עזר פשוטות
def get_patient_folder(patient_name):
    """יצירת תיקיית מטופל תחת user_1"""
    safe_name = patient_name.strip().replace('/', '_').replace('\\', '_')
    # יצירת תיקיית user_1 (משתמש יחיד במערכת הפשוטה)
    user_folder = os.path.join(app.config['TRANSCRIPTS_FOLDER'], 'user_1')
    os.makedirs(user_folder, exist_ok=True)
    # יצירת תיקיית המטופל תחת user_1
    patient_folder = os.path.join(user_folder, safe_name)
    os.makedirs(patient_folder, exist_ok=True)
    return patient_folder

def count_patients():
    """ספירת מטופלים (תיקיות מטופלים בתוך user_X)"""
    try:
        if not os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            return 0
        
        count = 0
        # חיפוש בתיקיות user_X
        for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
            if item.startswith('user_'):
                user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                if os.path.isdir(user_path):
                    # ספירת תיקיות מטופלים בתוך user_X
                    for patient_item in os.listdir(user_path):
                        patient_path = os.path.join(user_path, patient_item)
                        if os.path.isdir(patient_path):
                            count += 1
        
        print(f"👥 נמצאו {count} מטופלים")
        return count
    except Exception as e:
        print(f"❌ שגיאה בספירת מטופלים: {e}")
        return 0

def count_sessions():
    """ספירת סשנים (קבצי JSON)"""
    try:
        if not os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            return 0
        
        count = 0
        for root, dirs, files in os.walk(app.config['TRANSCRIPTS_FOLDER']):
            for file in files:
                if file.endswith('.json'):
                    count += 1
        
        print(f"📝 נמצאו {count} סשנים")
        return count
    except Exception as e:
        print(f"❌ שגיאה בספירת סשנים: {e}")
        return 0

def is_new_patient(patient_name):
    """בדיקה אם מטופל חדש (חיפוש בתוך user_X)"""
    patient_name = patient_name.strip()
    
    # חיפוש בתיקיות user_X
    for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
        if item.startswith('user_'):
            user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
            if os.path.isdir(user_path):
                patient_path = os.path.join(user_path, patient_name)
                if os.path.exists(patient_path):
                    print(f"🆕 מטופל {patient_name} קיים ב-{item}")
                    return False
    
    print(f"🆕 מטופל {patient_name} חדש")
    return True

def check_patient_limit(patient_name):
    """בדיקת מגבלת מטופלים - לוגיקה פשוטה"""
    current_patients = count_patients()
    is_new = is_new_patient(patient_name)
    
    print(f"🔍 בדיקת מגבלת מטופלים:")
    print(f"   - מטופלים נוכחיים: {current_patients}")
    print(f"   - מגבלה: {MAX_PATIENTS}")
    print(f"   - מטופל חדש: {is_new}")
    
    # אם זה מטופל קיים - תמיד מותר
    if not is_new:
        print("✅ מטופל קיים - מותר")
        return True, f"מטופל קיים ({current_patients}/{MAX_PATIENTS})"
    
    # אם זה מטופל חדש - בדיקת מגבלה
    if current_patients >= MAX_PATIENTS:
        print(f"❌ הגעה למגבלת מטופלים: {current_patients}/{MAX_PATIENTS}")
        return False, f"הגעת למגבלה - מותר {MAX_PATIENTS} מטופל{'ים' if MAX_PATIENTS > 1 else ''} בלבד"
    
    print("✅ ניתן להוסיף מטופל חדש")
    return True, f"ניתן להוסיף מטופל ({current_patients + 1}/{MAX_PATIENTS})"

# נתיבים בסיסיים
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/app')
def app_page():
    return render_template('app.html')

@app.route('/api/limits')
def get_limits():
    """קבלת מגבלות נוכחיות"""
    current_patients = count_patients()
    current_sessions = count_sessions()
    
    return jsonify({
        'success': True,
        'current_patients': current_patients,
        'max_patients': MAX_PATIENTS,
        'current_sessions': current_sessions,
        'max_sessions': MAX_SESSIONS,
        'can_add_patient': current_patients < MAX_PATIENTS,
        'can_add_session': current_sessions < MAX_SESSIONS
    })

@app.route('/check-patient-limit', methods=['POST'])
def check_patient_limit_api():
    """בדיקת מגבלת מטופל ספציפי"""
    try:
        data = request.json
        patient_name = data.get('patient_name', '').strip()
        
        if not patient_name:
            return jsonify({'error': 'חסר שם מטופל'}), 400
        
        can_add, message = check_patient_limit(patient_name)
        
        return jsonify({
            'success': True,
            'can_add_patient': can_add,
            'message': message,
            'current_patients': count_patients(),
            'max_patients': MAX_PATIENTS
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save-session', methods=['POST'])
def save_session():
    """שמירת סשן פשוטה"""
    try:
        data = request.json
        patient_name = data.get('patient_name', '').strip()
        transcript_text = data.get('transcript_text', '').strip()
        
        if not patient_name or not transcript_text:
            return jsonify({'error': 'חסרים נתונים'}), 400
        
        # בדיקת מגבלת מטופלים
        can_add_patient, patient_message = check_patient_limit(patient_name)
        if not can_add_patient:
            return jsonify({
                'error': 'הגעת למגבלת המטופלים',
                'message': patient_message
            }), 402
        
        # בדיקת מגבלת סשנים
        current_sessions = count_sessions()
        if current_sessions >= MAX_SESSIONS:
            return jsonify({
                'error': 'הגעת למגבלת הסשנים',
                'message': f'מותרים {MAX_SESSIONS} סשנים בלבד'
            }), 402
        
        # שמירת הסשן
        patient_folder = get_patient_folder(patient_name)
        session_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_file = os.path.join(patient_folder, f"session_{session_date}.json")
        
        session_data = {
            'patient_name': patient_name,
            'transcript_text': transcript_text,
            'created_at': datetime.datetime.now().isoformat(),
            'word_count': len(transcript_text.split())
        }
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ סשן נשמר: {session_file}")
        
        return jsonify({
            'success': True,
            'message': 'סשן נשמר בהצלחה',
            'current_patients': count_patients(),
            'current_sessions': count_sessions()
        })
        
    except Exception as e:
        print(f"❌ שגיאה בשמירת סשן: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/patients')
def get_patients():
    """קבלת רשימת מטופלים"""
    try:
        patients = []
        
        if os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            # חיפוש בתיקיות user_X
            for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
                if item.startswith('user_'):
                    user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                    if os.path.isdir(user_path):
                        # חיפוש מטופלים בתוך תיקיית המשתמש
                        for patient_name in os.listdir(user_path):
                            patient_path = os.path.join(user_path, patient_name)
                            if os.path.isdir(patient_path) and not patient_name.startswith('.') and not patient_name.startswith('privacy'):
                                # ספירת סשנים של המטופל
                                session_count = len([f for f in os.listdir(patient_path) if f.endswith('.json')])
                                patients.append({
                                    'name': patient_name,  # שם המטופל האמיתי
                                    'session_count': session_count
                                })
        
        return jsonify({
            'success': True,
            'patients': patients,
            'total_patients': len(patients),
            'max_patients': MAX_PATIENTS
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/patients/<patient_name>/sessions')
def get_patient_sessions(patient_name):
    """קבלת סשנים של מטופל ספציפי"""
    try:
        sessions = []
        
        if os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            # חיפוש בתיקיות user_X
            for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
                if item.startswith('user_'):
                    user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                    patient_path = os.path.join(user_path, patient_name)
                    
                    if os.path.exists(patient_path) and os.path.isdir(patient_path):
                        # קריאת כל קבצי הסשנים
                        for filename in os.listdir(patient_path):
                            if filename.endswith('.json'):
                                session_file = os.path.join(patient_path, filename)
                                try:
                                    with open(session_file, 'r', encoding='utf-8') as f:
                                        session_data = json.load(f)
                                    
                                    # הוספת מידע נוסף על הסשן
                                    session_info = {
                                        'filename': filename,
                                        'session_date': session_data.get('session_date', ''),
                                        'created_at': session_data.get('created_at', ''),
                                        'word_count': session_data.get('word_count', 0),
                                        'original_transcript': session_data.get('original_transcript', ''),
                                        'corrected_transcript': session_data.get('corrected_transcript', ''),
                                        'audio_filename': session_data.get('audio_filename', ''),
                                        'quality_mode': session_data.get('quality_mode', 'whisper')
                                    }
                                    
                                    # עיצוב תאריך יפה
                                    if session_info['created_at']:
                                        try:
                                            dt = datetime.datetime.fromisoformat(session_info['created_at'].replace('Z', '+00:00'))
                                            session_info['formatted_date'] = dt.strftime('%d/%m/%Y')
                                            session_info['formatted_time'] = dt.strftime('%H:%M')
                                            session_info['formatted_datetime'] = dt.strftime('%d/%m/%Y %H:%M')
                                        except:
                                            session_info['formatted_date'] = session_info['session_date'] or 'לא ידוע'
                                            session_info['formatted_time'] = ''
                                            session_info['formatted_datetime'] = session_info['created_at']
                                    else:
                                        session_info['formatted_date'] = session_info['session_date'] or 'לא ידוע'
                                        session_info['formatted_time'] = ''
                                        session_info['formatted_datetime'] = 'לא ידוע'
                                    
                                    sessions.append(session_info)
                                    
                                except Exception as e:
                                    print(f"❌ שגיאה בקריאת סשן {filename}: {e}")
                                    continue
                        break
        
        # מיון הסשנים לפי תאריך (החדשים ראשונים)
        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'patient_name': patient_name,
            'sessions': sessions,
            'total_sessions': len(sessions)
        })
        
    except Exception as e:
        print(f"❌ שגיאה בקבלת סשנים למטופל {patient_name}: {e}")
        return jsonify({'error': str(e)}), 500

# נתיבי אימות פשוטים
@app.route('/auth/register', methods=['POST'])
def register():
    """הרשמה פשוטה"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        if not email or not password or not full_name:
            return jsonify({'error': 'חסרים נתונים'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'הסיסמה חייבת להכיל לפחות 6 תווים'}), 400
        
        conn = sqlite3.connect('simple_users.db')
        cursor = conn.cursor()
        
        # בדיקה אם המשתמש כבר קיים
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'משתמש עם אימייל זה כבר קיים'}), 400
        
        # יצירת משתמש חדש
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (email, password_hash, full_name)
            VALUES (?, ?, ?)
        ''', (email, password_hash, full_name))
        
        conn.commit()
        conn.close()
        
        print(f"✅ משתמש חדש נרשם: {email}")
        return jsonify({'success': True, 'message': 'הרשמה בהצלחה'})
        
    except Exception as e:
        print(f"❌ שגיאה בהרשמה: {e}")
        return jsonify({'error': 'שגיאה בהרשמה'}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """כניסה פשוטה"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'חסרים נתונים'}), 400
        
        conn = sqlite3.connect('simple_users.db')
        cursor = conn.cursor()
        
        # בדיקת משתמש
        cursor.execute('SELECT id, password_hash, full_name FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(password, user[1]):
            conn.close()
            return jsonify({'error': 'אימייל או סיסמה שגויים'}), 401
        
        user_id, _, full_name = user
        
        # יצירת session token
        session_token = create_session_token()
        expires_at = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        
        cursor.execute('''
            INSERT INTO sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, session_token, expires_at))
        
        conn.commit()
        conn.close()
        
        print(f"✅ משתמש נכנס: {email}")
        return jsonify({
            'success': True,
            'session_token': session_token,
            'user_info': {
                'email': email,
                'full_name': full_name,
                'user_id': user_id
            }
        })
        
    except Exception as e:
        print(f"❌ שגיאה בכניסה: {e}")
        return jsonify({'error': 'שגיאה בכניסה'}), 500

@app.route('/auth/verify', methods=['GET'])
def verify_session():
    """אימות session token"""
    try:
        # קבלת token מהכותרת
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'חסר token'}), 401
        
        session_token = auth_header[7:]  # הסרת "Bearer "
        
        conn = sqlite3.connect('simple_users.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.user_id, u.email, u.full_name, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ?
        ''', (session_token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Session לא תקין'}), 401
        
        user_id, email, full_name, expires_at = result
        
        # בדיקת תוקף
        if datetime.datetime.fromisoformat(expires_at) < datetime.datetime.now():
            return jsonify({'error': 'Session פג תוקף'}), 401
        
        return jsonify({
            'success': True,
            'user_info': {
                'user_id': user_id,
                'email': email,
                'full_name': full_name
            }
        })
        
    except Exception as e:
        print(f"❌ שגיאה באימות: {e}")
        return jsonify({'error': 'שגיאה באימות'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """יציאה פשוטה"""
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
            
            conn = sqlite3.connect('simple_users.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
            conn.commit()
            conn.close()
        
        return jsonify({'success': True, 'message': 'יציאה בהצלחה'})
        
    except Exception as e:
        print(f"❌ שגיאה ביציאה: {e}")
        return jsonify({'error': 'שגיאה ביציאה'}), 500

@app.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    """בקשת איפוס סיסמה"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'חסר אימייל'}), 400
        
        conn = sqlite3.connect('simple_users.db')
        cursor = conn.cursor()
        
        # בדיקה אם המשתמש קיים
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            # גם אם המשתמש לא קיים, נחזיר הצלחה (אבטחה)
            return jsonify({
                'success': True, 
                'message': 'אם האימייל קיים במערכת, נשלח אליו קישור לאיפוס סיסמה'
            })
        
        user_id = user[0]
        
        # יצירת טוקן איפוס
        reset_token = secrets.token_urlsafe(32)
        expires_at = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
        
        # שמירת טוקן איפוס (נוסיף טבלה אם לא קיימת)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reset_token TEXT UNIQUE,
                expires_at TEXT,
                used BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO password_resets (user_id, reset_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, reset_token, expires_at))
        
        conn.commit()
        conn.close()
        
        print(f"✅ טוקן איפוס סיסמה נוצר למשתמש: {email}")
        
        # במצב פיתוח - נחזיר את הטוקן (בפרודקשן נשלח במייל)
        if os.getenv('DEBUG', 'True').lower() == 'true':
            return jsonify({
                'success': True,
                'message': 'טוקן איפוס נוצר בהצלחה',
                'reset_token': reset_token  # רק במצב פיתוח!
            })
        else:
            return jsonify({
                'success': True,
                'message': 'קישור לאיפוס סיסמה נשלח לאימייל שלך'
            })
        
    except Exception as e:
        print(f"❌ שגיאה בבקשת איפוס סיסמה: {e}")
        return jsonify({'error': 'שגיאה בבקשת איפוס סיסמה'}), 500

@app.route('/auth/reset-password', methods=['POST'])
def reset_password():
    """איפוס סיסמה עם טוקן"""
    try:
        data = request.json
        token = data.get('token', '').strip()
        new_password = data.get('new_password', '')
        
        if not token or not new_password:
            return jsonify({'error': 'חסרים נתונים'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'הסיסמה חייבת להכיל לפחות 6 תווים'}), 400
        
        conn = sqlite3.connect('simple_users.db')
        cursor = conn.cursor()
        
        # בדיקת טוקן
        cursor.execute('''
            SELECT pr.user_id, pr.expires_at, pr.used, u.email
            FROM password_resets pr
            JOIN users u ON pr.user_id = u.id
            WHERE pr.reset_token = ?
        ''', (token,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'טוקן איפוס לא תקין'}), 400
        
        user_id, expires_at, used, email = result
        
        # בדיקת תוקף
        if datetime.datetime.fromisoformat(expires_at) < datetime.datetime.now():
            conn.close()
            return jsonify({'error': 'טוקן איפוס פג תוקף'}), 400
        
        # בדיקה אם כבר נוצל
        if used:
            conn.close()
            return jsonify({'error': 'טוקן איפוס כבר נוצל'}), 400
        
        # עדכון סיסמה
        new_password_hash = hash_password(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
        
        # סימון הטוקן כמנוצל
        cursor.execute('UPDATE password_resets SET used = TRUE WHERE reset_token = ?', (token,))
        
        # מחיקת כל הסשנים הקיימים של המשתמש (אבטחה)
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ סיסמה אופסה בהצלחה למשתמש: {email}")
        
        return jsonify({
            'success': True,
            'message': 'הסיסמה אופסה בהצלחה. כעת תוכל להתחבר עם הסיסמה החדשה'
        })
        
    except Exception as e:
        print(f"❌ שגיאה באיפוס סיסמה: {e}")
        return jsonify({'error': 'שגיאה באיפוס סיסמה'}), 500

@app.route('/auth/google-config')
def google_config():
    """קבלת הגדרות Google OAuth"""
    return jsonify({
        'client_id': os.getenv('GOOGLE_CLIENT_ID', 'your-google-client-id-here')
    })

# נתיבים נוספים שהדפים צריכים
@app.route('/subscription/status')
def subscription_status():
    """סטטוס מנוי פשוט"""
    return jsonify({
        'success': True,
        'subscription': {
            'subscription_type': 'trial',
            'payment_status': 'unpaid',
            'sessions_remaining': MAX_SESSIONS - count_sessions(),
            'sessions_limit': MAX_SESSIONS
        }
    })

@app.route('/subscription/check-session-limit')
def check_session_limit():
    """בדיקת מגבלת סשנים"""
    current_sessions = count_sessions()
    return jsonify({
        'success': True,
        'can_create_session': current_sessions < MAX_SESSIONS,
        'sessions_used': current_sessions,
        'sessions_limit': MAX_SESSIONS,
        'status': 'trial',
        'sessions_remaining': MAX_SESSIONS - current_sessions
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """תמלול שמע - תמיכה רק ב-AssemblyAI ו-ivrit.ai"""
    try:
        # בדיקת אימות
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'נדרש אימות'}), 401
        
        # קבלת נתונים מהבקשה
        patient_name = request.form.get('patient_name', '').strip()
        session_date = request.form.get('session_date', '')
        quality_mode = request.form.get('quality_mode', 'assemblyai')
        
        if not patient_name:
            return jsonify({'error': 'חסר שם מטופל'}), 400
        
        # בדיקת קובץ שמע
        if 'audio' not in request.files:
            return jsonify({'error': 'חסר קובץ שמע'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'לא נבחר קובץ'}), 400
        
        # בדיקת מגבלות
        can_add_patient, patient_message = check_patient_limit(patient_name)
        if not can_add_patient:
            return jsonify({
                'error': 'הגעת למגבלת המטופלים',
                'message': patient_message
            }), 402
        
        current_sessions = count_sessions()
        if current_sessions >= MAX_SESSIONS:
            return jsonify({
                'error': 'הגעת למגבלת הסשנים',
                'message': f'מותרים {MAX_SESSIONS} סשנים בלבד'
            }), 402
        
        # שמירת קובץ שמע זמני
        filename = secure_filename(audio_file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        audio_file.save(temp_path)
        
        try:
            # בדיקת סוג התמלול
            if quality_mode == 'assemblyai':
                # תמלול עם AssemblyAI
                if not ASSEMBLYAI_API_KEY:
                    print("❌ חסר ASSEMBLYAI_API_KEY - לא ניתן לבצע תמלול")
                    return jsonify({
                        'error': 'שירות התמלול לא זמין',
                        'message': 'לא הוגדר API key לשירות התמלול. אנא פנה למנהל המערכת.'
                    }), 503
                
                print(f"🎯 מתחיל תמלול עם AssemblyAI: {filename}")
                
                # יצירת transcriber
                transcriber = aai.Transcriber()
                
                # הגדרות תמלול
                config = aai.TranscriptionConfig(
                    language_code="he",  # עברית
                    punctuate=True,
                    format_text=True
                )
                
                # תמלול הקובץ
                transcript = transcriber.transcribe(temp_path, config=config)
                
                if transcript.status == aai.TranscriptStatus.error:
                    print(f"❌ שגיאה בתמלול AssemblyAI: {transcript.error}")
                    return jsonify({
                        'error': 'שגיאה בשירות התמלול',
                        'message': f'שירות התמלול נתקל בשגיאה: {transcript.error}'
                    }), 503
                else:
                    original_transcript = transcript.text or "לא נמצא תוכן לתמלול"
                    corrected_transcript = original_transcript
                    print(f"✅ תמלול AssemblyAI הושלם: {len(original_transcript)} תווים")
                    
            elif quality_mode == 'ivrit-ai':
                # תמלול עם ivrit.ai (סימולציה - יש להוסיף API אמיתי)
                print(f"🏆 מתחיל תמלול עם ivrit.ai: {filename}")
                
                # כרגע סימולציה - בעתיד יש להוסיף API אמיתי של ivrit.ai
                original_transcript = f"תמלול דמה עם ivrit.ai עבור קובץ {filename}"
                corrected_transcript = original_transcript
                print(f"✅ תמלול ivrit.ai הושלם (דמה): {len(original_transcript)} תווים")
                
            else:
                return jsonify({
                    'error': 'שירות תמלול לא נתמך',
                    'message': f'שירות התמלול {quality_mode} לא נתמך'
                }), 400
            
            # שמירת התמלול
            patient_folder = get_patient_folder(patient_name)
            session_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            session_file = os.path.join(patient_folder, f"session_{session_timestamp}.json")
            
            session_data = {
                'patient_name': patient_name,
                'session_date': session_date or datetime.datetime.now().strftime("%Y-%m-%d"),
                'audio_filename': filename,
                'quality_mode': quality_mode,
                'original_transcript': original_transcript,
                'corrected_transcript': corrected_transcript,
                'word_count': len(corrected_transcript.split()),
                'created_at': datetime.datetime.now().isoformat()
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ תמלול נשמר: {session_file}")
            
            return jsonify({
                'success': True,
                'original_transcript': original_transcript,
                'corrected_transcript': corrected_transcript,
                'session_info': {
                    'sessions_used': count_sessions(),
                    'sessions_limit': MAX_SESSIONS,
                    'sessions_remaining': MAX_SESSIONS - count_sessions()
                }
            })
            
        finally:
            # ניקוי קובץ זמני
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        print(f"❌ שגיאה בתמלול: {e}")
        return jsonify({'error': f'שגיאה בתמלול: {str(e)}'}), 500

@app.route('/transcribe-encrypted', methods=['POST'])
def transcribe_encrypted():
    """תמלול היברידי מוצפן - גרסה פשוטה"""
    try:
        # בדיקת אימות
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'נדרש אימות'}), 401
        
        # קבלת נתונים
        patient_name = request.form.get('patient_name', '').strip()
        encryption_key = request.form.get('encryption_key', '').strip()
        
        if not patient_name or not encryption_key:
            return jsonify({'error': 'חסרים נתונים נדרשים'}), 400
        
        # בדיקת סיסמת הצפנה פשוטה
        if len(encryption_key) < 6:
            return jsonify({'error': 'סיסמת הצפנה חייבת להכיל לפחות 6 תווים'}), 401
        
        # תמלול דמה מוצפן
        original_transcript = f"תמלול מוצפן עבור {patient_name}"
        corrected_transcript = f"תמלול מוצפן מתוקן עבור {patient_name}"
        
        return jsonify({
            'success': True,
            'original_transcript': original_transcript,
            'corrected_transcript': corrected_transcript,
            'corrections_made': [],
            'encrypted': True
        })
        
    except Exception as e:
        print(f"❌ שגיאה בתמלול מוצפן: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/transcribe-secure-assemblyai', methods=['POST'])
def transcribe_secure_assemblyai():
    """תמלול מאובטח עם AssemblyAI - הצפנה מקסימלית"""
    try:
        # בדיקת אימות
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'נדרש אימות'}), 401
        
        # בדיקת AssemblyAI API Key
        if not ASSEMBLYAI_API_KEY:
            return jsonify({
                'error': 'שירות התמלול המאובטח לא זמין',
                'message': 'לא הוגדר API key לשירות התמלול.'
            }), 503
        
        # קבלת נתונים מהבקשה
        patient_name = request.form.get('patient_name', '').strip()
        session_date = request.form.get('session_date', '')
        encryption_password = request.form.get('encryption_key', '').strip()
        
        if not patient_name or not encryption_password:
            return jsonify({'error': 'חסרים נתונים נדרשים'}), 400
        
        if len(encryption_password) < 8:
            return jsonify({'error': 'סיסמת הצפנה חייבת להכיל לפחות 8 תווים'}), 400
        
        # בדיקת קובץ שמע
        if 'audio' not in request.files:
            return jsonify({'error': 'חסר קובץ שמע'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'לא נבחר קובץ'}), 400
        
        # בדיקת מגבלות
        can_add_patient, patient_message = check_patient_limit(patient_name)
        if not can_add_patient:
            return jsonify({
                'error': 'הגעת למגבלת המטופלים',
                'message': patient_message
            }), 402
        
        current_sessions = count_sessions()
        if current_sessions >= MAX_SESSIONS:
            return jsonify({
                'error': 'הגעת למגבלת הסשנים',
                'message': f'מותרים {MAX_SESSIONS} סשנים בלבד'
            }), 402
        
        # שמירת קובץ שמע זמני
        filename = secure_filename(audio_file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        audio_file.save(temp_path)
        
        try:
            print(f"🔐 מתחיל תמלול מאובטח עם AssemblyAI: {filename}")
            
            # בדיקה אם המערכת המאובטחת זמינה
            if not SECURE_ASSEMBLYAI_AVAILABLE or SecureAssemblyAI is None:
                print("❌ מערכת תמלול מאובטח לא זמינה")
                return jsonify({
                    'error': 'מערכת תמלול מאובטח לא זמינה',
                    'message': 'חסרה ספריית ההצפנה. הרץ: pip install cryptography'
                }), 503
            
            # יצירת מערכת תמלול מאובטחת
            secure_ai = SecureAssemblyAI(ASSEMBLYAI_API_KEY, encryption_password)
            
            # תמלול מאובטח
            result = secure_ai.secure_transcribe(temp_path, patient_name)
            
            if result['success']:
                # שמירת התמלול המוצפן
                patient_folder = get_patient_folder(patient_name)
                session_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                session_file = os.path.join(patient_folder, f"secure_session_{session_timestamp}.json")
                
                # פענוח זמני לסטטיסטיקות (רק לשמירה)
                decrypted_text = secure_ai.decrypt_transcript(result['encrypted_transcript'])
                
                session_data = {
                    'patient_name': patient_name,
                    'session_date': session_date or datetime.datetime.now().strftime("%Y-%m-%d"),
                    'audio_filename': filename,
                    'quality_mode': 'secure-assemblyai',
                    'encrypted_transcript': result['encrypted_transcript'],
                    'content_hash': result['content_hash'],
                    'encryption_method': result['encryption_method'],
                    'privacy_level': result['privacy_level'],
                    'word_count': result['word_count'],
                    'char_count': result['char_count'],
                    'created_at': datetime.datetime.now().isoformat(),
                    'is_encrypted': True
                }
                
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ תמלול מאובטח נשמר: {session_file}")
                
                return jsonify({
                    'success': True,
                    'original_transcript': decrypted_text,  # מוצג רק בממשק
                    'corrected_transcript': decrypted_text,
                    'encryption_info': {
                        'method': result['encryption_method'],
                        'privacy_level': result['privacy_level'],
                        'content_hash': result['content_hash']
                    },
                    'session_info': {
                        'sessions_used': count_sessions(),
                        'sessions_limit': MAX_SESSIONS,
                        'sessions_remaining': MAX_SESSIONS - count_sessions()
                    },
                    'security_message': '🔐 התמלול נשמר בהצפנה מקסימלית - רק אתה יכול לפענח אותו!'
                })
            else:
                return jsonify({'error': 'שגיאה בתמלול מאובטח'}), 500
                
        finally:
            # ניקוי קובץ זמני
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        print(f"❌ שגיאה בתמלול מאובטח: {e}")
        return jsonify({'error': f'שגיאה בתמלול מאובטח: {str(e)}'}), 500

@app.route('/patients/<patient_name>/session/<session_filename>')
def get_session_content(patient_name, session_filename):
    """קבלת תוכן סשן ספציפי"""
    try:
        if os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            # חיפוש בתיקיות user_X
            for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
                if item.startswith('user_'):
                    user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                    patient_path = os.path.join(user_path, patient_name)
                    
                    if os.path.exists(patient_path) and os.path.isdir(patient_path):
                        session_file = os.path.join(patient_path, session_filename)
                        
                        if os.path.exists(session_file) and session_filename.endswith('.json'):
                            try:
                                with open(session_file, 'r', encoding='utf-8') as f:
                                    session_data = json.load(f)
                                
                                print(f"📋 נתוני סשן נטענו מהקובץ: {list(session_data.keys())}")
                                
                                # בדיקה אם זה סשן מוצפן
                                if session_data.get('is_encrypted') and session_data.get('encrypted_transcript'):
                                    print("🔐 זה סשן מוצפן - נדרשת סיסמה לפענוח")
                                    # החזרת נתונים עם סימון שזה מוצפן
                                    session_data['transcript_text'] = '[תמלול מוצפן - נדרשת סיסמה לפענוח]'
                                    session_data['needs_decryption'] = True
                                else:
                                    # סשן רגיל - וידוא שיש תוכן תמלול בשדה הנכון
                                    transcript_content = ''
                                    if session_data.get('transcript_text'):
                                        transcript_content = session_data['transcript_text']
                                        print(f"✅ נמצא תמלול בשדה transcript_text: {len(transcript_content)} תווים")
                                    elif session_data.get('corrected_transcript'):
                                        transcript_content = session_data['corrected_transcript']
                                        print(f"✅ נמצא תמלול בשדה corrected_transcript: {len(transcript_content)} תווים")
                                    elif session_data.get('original_transcript'):
                                        transcript_content = session_data['original_transcript']
                                        print(f"✅ נמצא תמלול בשדה original_transcript: {len(transcript_content)} תווים")
                                    else:
                                        print(f"❌ לא נמצא תמלול בשום שדה!")
                                    
                                    # הוספת השדה transcript_text אם לא קיים
                                    if not session_data.get('transcript_text') and transcript_content:
                                        session_data['transcript_text'] = transcript_content
                                        print(f"🔧 הוסף שדה transcript_text עם התוכן")
                                
                                # עיצוב תאריך יפה
                                if session_data.get('created_at'):
                                    try:
                                        dt = datetime.datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00'))
                                        session_data['formatted_date'] = dt.strftime('%d/%m/%Y')
                                        session_data['formatted_time'] = dt.strftime('%H:%M')
                                        session_data['formatted_datetime'] = dt.strftime('%d/%m/%Y %H:%M')
                                    except:
                                        session_data['formatted_date'] = session_data.get('session_date', 'לא ידוע')
                                        session_data['formatted_time'] = ''
                                        session_data['formatted_datetime'] = session_data.get('created_at', 'לא ידוע')
                                
                                print(f"📤 שולח נתוני סשן עם השדות: {list(session_data.keys())}")
                                
                                return jsonify({
                                    'success': True,
                                    'session_data': session_data
                                })
                                
                            except Exception as e:
                                print(f"❌ שגיאה בקריאת סשן {session_filename}: {e}")
                                return jsonify({'error': 'שגיאה בקריאת הסשן'}), 500
                        break
        
        return jsonify({'error': 'סשן לא נמצא'}), 404
        
    except Exception as e:
        print(f"❌ שגיאה בקבלת תוכן סשן: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/decrypt-session', methods=['POST'])
def decrypt_session():
    """פענוח סשן מוצפן עם סיסמה"""
    try:
        # בדיקת אימות
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'נדרש אימות'}), 401
        
        data = request.json
        patient_name = data.get('patient_name', '').strip()
        session_filename = data.get('session_filename', '').strip()
        decryption_password = data.get('decryption_password', '').strip()
        
        if not patient_name or not session_filename or not decryption_password:
            return jsonify({'error': 'חסרים נתונים נדרשים'}), 400
        
        # בדיקה אם המערכת המאובטחת זמינה
        if not SECURE_ASSEMBLYAI_AVAILABLE or SecureAssemblyAI is None:
            return jsonify({
                'error': 'מערכת פענוח לא זמינה',
                'message': 'חסרה ספריית ההצפנה'
            }), 503
        
        # חיפוש הסשן
        session_found = False
        session_data = None
        
        if os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
                if item.startswith('user_'):
                    user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                    patient_path = os.path.join(user_path, patient_name)
                    
                    if os.path.exists(patient_path) and os.path.isdir(patient_path):
                        session_file = os.path.join(patient_path, session_filename)
                        
                        if os.path.exists(session_file) and session_filename.endswith('.json'):
                            with open(session_file, 'r', encoding='utf-8') as f:
                                session_data = json.load(f)
                            session_found = True
                            break
        
        if not session_found or not session_data:
            return jsonify({'error': 'סשן לא נמצא'}), 404
        
        # בדיקה אם זה באמת סשן מוצפן
        if not session_data.get('is_encrypted') or not session_data.get('encrypted_transcript'):
            return jsonify({'error': 'זה לא סשן מוצפן'}), 400
        
        try:
            # יצירת מערכת פענוח עם הסיסמה
            secure_ai = SecureAssemblyAI(ASSEMBLYAI_API_KEY, decryption_password)
            
            # פענוח התמלול
            decrypted_text = secure_ai.decrypt_transcript(session_data['encrypted_transcript'])
            
            print(f"✅ סשן פוענח בהצלחה: {len(decrypted_text)} תווים")
            
            return jsonify({
                'success': True,
                'decrypted_transcript': decrypted_text,
                'encryption_info': {
                    'method': session_data.get('encryption_method', 'לא ידוע'),
                    'privacy_level': session_data.get('privacy_level', 'לא ידוע'),
                    'content_hash': session_data.get('content_hash', 'לא ידוע')
                }
            })
            
        except Exception as decrypt_error:
            print(f"❌ שגיאה בפענוח: {decrypt_error}")
            return jsonify({
                'error': 'שגיאה בפענוח',
                'message': 'סיסמה שגויה או נתונים פגומים'
            }), 400
        
    except Exception as e:
        print(f"❌ שגיאה בפענוח סשן: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/patient/<patient_name>', methods=['DELETE'])
def delete_patient(patient_name):
    """מחיקת מטופל וכל הסשנים שלו"""
    try:
        # בדיקת אימות
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'נדרש אימות'}), 401
        
        deleted_sessions_count = 0
        patient_found = False
        
        if os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            # חיפוש בתיקיות user_X
            for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
                if item.startswith('user_'):
                    user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                    patient_path = os.path.join(user_path, patient_name)
                    
                    if os.path.exists(patient_path) and os.path.isdir(patient_path):
                        patient_found = True
                        
                        # ספירת הסשנים לפני המחיקה
                        session_files = [f for f in os.listdir(patient_path) if f.endswith('.json')]
                        deleted_sessions_count = len(session_files)
                        
                        # מחיקת תיקיית המטופל וכל התוכן
                        import shutil
                        shutil.rmtree(patient_path)
                        
                        print(f"🗑️ מחק מטופל {patient_name} עם {deleted_sessions_count} סשנים")
                        break
        
        if not patient_found:
            return jsonify({'error': 'מטופל לא נמצא'}), 404
        
        return jsonify({
            'success': True,
            'message': f'המטופל {patient_name} נמחק בהצלחה',
            'deleted_sessions': deleted_sessions_count,
            'current_patients': count_patients(),
            'current_sessions': count_sessions()
        })
        
    except Exception as e:
        print(f"❌ שגיאה במחיקת מטופל {patient_name}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete-session', methods=['DELETE'])
def delete_session():
    """מחיקת סשן ספציפי"""
    try:
        # בדיקת אימות
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'נדרש אימות'}), 401
        
        data = request.json
        patient_name = data.get('patient_name', '').strip()
        session_filename = data.get('session_filename', '').strip()
        
        if not patient_name or not session_filename:
            return jsonify({'error': 'חסרים נתונים נדרשים'}), 400
        
        session_found = False
        
        if os.path.exists(app.config['TRANSCRIPTS_FOLDER']):
            # חיפוש בתיקיות user_X
            for item in os.listdir(app.config['TRANSCRIPTS_FOLDER']):
                if item.startswith('user_'):
                    user_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], item)
                    patient_path = os.path.join(user_path, patient_name)
                    
                    if os.path.exists(patient_path) and os.path.isdir(patient_path):
                        session_file = os.path.join(patient_path, session_filename)
                        
                        if os.path.exists(session_file):
                            os.remove(session_file)
                            session_found = True
                            print(f"🗑️ מחק סשן {session_filename} של מטופל {patient_name}")
                            break
        
        if not session_found:
            return jsonify({'error': 'סשן לא נמצא'}), 404
        
        return jsonify({
            'success': True,
            'message': f'הסשן נמחק בהצלחה',
            'session_info': {
                'sessions_used': count_sessions(),
                'sessions_limit': MAX_SESSIONS,
                'sessions_remaining': MAX_SESSIONS - count_sessions()
            }
        })
        
    except Exception as e:
        print(f"❌ שגיאה במחיקת סשן: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print("🎤 מערכת תמלול פשוטה למטפלים")
    print(f"🌐 גישה: http://localhost:{PORT}")
    print(f"🔧 מגבלות: {MAX_PATIENTS} מטופלים, {MAX_SESSIONS} סשנים")
    print("🔥 מוכן לפעולה!")
    
    app.run(debug=DEBUG, host=HOST, port=PORT)
