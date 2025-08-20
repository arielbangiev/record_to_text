# auth_manager.py - מערכת אימות מודרנית
import os
import json
import hashlib
import secrets
import datetime
from flask import session, request
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import sqlite3
import bcrypt
from dotenv import load_dotenv

load_dotenv()

class AuthManager:
    def __init__(self):
        self.db_path = 'users.db'
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')
        
        # Load free user limits from environment variables
        self.free_max_patients = int(os.getenv('FREE_MAX_PATIENTS', '1'))
        self.free_max_sessions = int(os.getenv('FREE_MAX_SESSIONS', '5'))
        
        self.init_database()
    
    def init_database(self):
        """יצירת טבלת משתמשים"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                full_name TEXT,
                google_id TEXT,
                subscription_type TEXT DEFAULT 'trial',
                subscription_expires TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                is_active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                usage_limit INTEGER DEFAULT 50,
                free_sessions_used INTEGER DEFAULT 0,
                free_sessions_limit INTEGER DEFAULT {self.free_max_sessions},
                payment_status TEXT DEFAULT 'unpaid'
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
        
        # Update existing users who might have the old default limit
        cursor.execute(f'''
            UPDATE users 
            SET free_sessions_limit = {self.free_max_sessions} 
            WHERE free_sessions_limit = 1 AND subscription_type = 'trial'
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        """הצפנת סיסמה"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, password_hash):
        """אימות סיסמה"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def register_user(self, email, password, full_name):
        """רישום משתמש חדש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # בדיקה אם המשתמש כבר קיים
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return False, 'משתמש עם אימייל זה כבר קיים'
            
            # הצפנת סיסמה
            password_hash = self.hash_password(password)
            
            # הוספת משתמש חדש עם הגבלות מהמשתני סביבה
            cursor.execute('''
                INSERT INTO users (email, password_hash, full_name, subscription_type, subscription_expires, 
                                 free_sessions_used, free_sessions_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (email, password_hash, full_name, 'trial', 
                  (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat(), 
                  0, self.free_max_sessions))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            print(f"✅ משתמש חדש נרשם: {email}")
            return True, user_id
            
        except Exception as e:
            print(f"❌ שגיאה ברישום משתמש: {str(e)}")
            return False, str(e)
    
    def login_user(self, email, password):
        """כניסת משתמש עם אימייל וסיסמה"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, password_hash, full_name, is_active, subscription_expires
                FROM users WHERE email = ?
            ''', (email,))
            
            user = cursor.fetchone()
            if not user:
                return False, 'משתמש לא נמצא'
            
            user_id, password_hash, full_name, is_active, subscription_expires = user
            
            if not is_active:
                return False, 'חשבון לא פעיל'
            
            if not self.verify_password(password, password_hash):
                return False, 'סיסמה שגויה'
            
            # בדיקת תוקף מנוי
            if subscription_expires:
                expires_date = datetime.datetime.fromisoformat(subscription_expires)
                if expires_date < datetime.datetime.now():
                    return False, 'המנוי פג תוקף'
            
            # עדכון זמן כניסה אחרון
            cursor.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.datetime.now().isoformat(), user_id))
            
            # יצירת session token
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
            
            cursor.execute('''
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            print(f"✅ משתמש נכנס: {email}")
            return True, {
                'user_id': user_id,
                'email': email,
                'full_name': full_name,
                'session_token': session_token
            }
            
        except Exception as e:
            print(f"❌ שגיאה בכניסת משתמש: {str(e)}")
            return False, str(e)
    
    def login_with_google(self, google_token):
        """כניסה עם Google"""
        try:
            if not self.google_client_id or self.google_client_id == 'your-google-client-id-here':
                return False, 'Google OAuth לא מוגדר במערכת'
            
            # אימות הטוקן של Google
            try:
                idinfo = id_token.verify_oauth2_token(
                    google_token, google_requests.Request(), self.google_client_id)
                
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    return False, 'טוקן Google לא תקין'
                
                # הסרת הגבלת המשתמש - כעת כל המשתמשים מורשים
                user_email = idinfo.get('email', '')
                    
            except ValueError as ve:
                print(f"Google token verification failed: {str(ve)}")
                return False, f'אימות טוקן Google נכשל: {str(ve)}'
            
            google_id = idinfo['sub']
            email = idinfo['email']
            full_name = idinfo.get('name', '')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # בדיקה אם המשתמש קיים
            cursor.execute('SELECT id, full_name, is_active FROM users WHERE google_id = ? OR email = ?', 
                          (google_id, email))
            user = cursor.fetchone()
            
            if user:
                user_id, existing_name, is_active = user
                if not is_active:
                    return False, 'חשבון לא פעיל'
                
                # עדכון Google ID אם לא קיים ועדכון זמן כניסה
                cursor.execute('''
                    UPDATE users SET google_id = ?, last_login = ?, full_name = ? WHERE id = ?
                ''', (google_id, datetime.datetime.now().isoformat(), full_name or existing_name, user_id))
                
                final_name = full_name or existing_name
            else:
                # יצירת משתמש חדש עם הגבלות מהמשתני סביבה
                cursor.execute('''
                    INSERT INTO users (email, google_id, full_name, subscription_type, subscription_expires, 
                                     free_sessions_used, free_sessions_limit)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (email, google_id, full_name, 'trial',
                      (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat(), 
                      0, self.free_max_sessions))
                user_id = cursor.lastrowid
                final_name = full_name
            
            # יצירת session token
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
            
            cursor.execute('''
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            print(f"✅ כניסה עם Google: {email}")
            return True, {
                'user_id': user_id,
                'email': email,
                'full_name': final_name,
                'session_token': session_token
            }
            
        except Exception as e:
            print(f"❌ שגיאה בכניסה עם Google: {str(e)}")
            return False, f'שגיאה בכניסה עם Google: {str(e)}'
    
    def verify_session(self, session_token):
        """אימות session token"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.user_id, u.email, u.full_name, u.subscription_expires, u.usage_count, u.usage_limit, 
                       u.subscription_type, u.free_sessions_used, u.free_sessions_limit, u.payment_status
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.expires_at > ? AND u.is_active = 1
            ''', (session_token, datetime.datetime.now().isoformat()))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                user_id, email, full_name, subscription_expires, usage_count, usage_limit, subscription_type, free_sessions_used, free_sessions_limit, payment_status = result
                
                # בדיקת תוקף מנוי
                if subscription_expires:
                    expires_date = datetime.datetime.fromisoformat(subscription_expires)
                    if expires_date < datetime.datetime.now():
                        return False, 'המנוי פג תוקף'
                
                return True, {
                    'user_id': user_id,
                    'email': email,
                    'full_name': full_name,
                    'usage_count': usage_count,
                    'usage_limit': usage_limit,
                    'subscription_type': subscription_type,
                    'free_sessions_used': free_sessions_used,
                    'free_sessions_limit': free_sessions_limit,
                    'payment_status': payment_status
                }
            
            return False, 'Session לא תקין'
            
        except Exception as e:
            print(f"❌ שגיאה באימות session: {str(e)}")
            return False, str(e)
    
    def logout_user(self, session_token):
        """יציאת משתמש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה ביציאת משתמש: {str(e)}")
            return False
    
    def increment_usage(self, user_id):
        """הגדלת מונה השימוש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET usage_count = usage_count + 1 WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בעדכון מונה שימוש: {str(e)}")
            return False
    
    def check_usage_limit(self, user_id):
        """בדיקת מגבלת שימוש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT usage_count, usage_limit, subscription_type
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                usage_count, usage_limit, subscription_type = result
                
                # מנוי פרימיום = ללא הגבלה
                if subscription_type in ['premium', 'professional']:
                    return True, usage_count, -1
                
                # בדיקת מגבלה
                if usage_count >= usage_limit:
                    return False, usage_count, usage_limit
                
                return True, usage_count, usage_limit
            
            return False, 0, 0
            
        except Exception as e:
            print(f"❌ שגיאה בבדיקת מגבלת שימוש: {str(e)}")
            return False, 0, 0
    
    def get_user_info(self, user_id):
        """קבלת מידע משתמש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT email, full_name, subscription_type, subscription_expires, 
                       usage_count, usage_limit, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                email, full_name, subscription_type, subscription_expires, usage_count, usage_limit, created_at, last_login = result
                
                return {
                    'email': email,
                    'full_name': full_name,
                    'subscription_type': subscription_type,
                    'subscription_expires': subscription_expires,
                    'usage_count': usage_count,
                    'usage_limit': usage_limit,
                    'created_at': created_at,
                    'last_login': last_login
                }
            
            return None
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת מידע משתמש: {str(e)}")
            return None
    
    def generate_password_reset_token(self, email):
        """יצירת טוקן לאיפוס סיסמה"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # בדיקה אם המשתמש קיים
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                return False, 'משתמש עם אימייל זה לא נמצא'
            
            user_id = user[0]
            
            # יצירת טוקן איפוס
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)  # תוקף של שעה
            
            # יצירת טבלת טוקני איפוס אם לא קיימת
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    token TEXT UNIQUE,
                    expires_at TEXT,
                    used BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # הוספת הטוקן
            cursor.execute('''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, reset_token, expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            print(f"✅ טוקן איפוס סיסמה נוצר עבור: {email}")
            return True, reset_token
            
        except Exception as e:
            print(f"❌ שגיאה ביצירת טוקן איפוס: {str(e)}")
            return False, str(e)
    
    def reset_password(self, token, new_password):
        """איפוס סיסמה באמצעות טוקן"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # בדיקת תוקף הטוקן
            cursor.execute('''
                SELECT prt.user_id, u.email 
                FROM password_reset_tokens prt
                JOIN users u ON prt.user_id = u.id
                WHERE prt.token = ? AND prt.expires_at > ? AND prt.used = 0
            ''', (token, datetime.datetime.now().isoformat()))
            
            result = cursor.fetchone()
            
            if not result:
                return False, 'טוקן לא תקין או פג תוקף'
            
            user_id, email = result
            
            # הצפנת הסיסמה החדשה
            new_password_hash = self.hash_password(new_password)
            
            # עדכון הסיסמה
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE id = ?
            ''', (new_password_hash, user_id))
            
            # סימון הטוקן כמשומש
            cursor.execute('''
                UPDATE password_reset_tokens SET used = 1 WHERE token = ?
            ''', (token,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ סיסמה אופסה בהצלחה עבור: {email}")
            return True, 'הסיסמה אופסה בהצלחה'
            
        except Exception as e:
            print(f"❌ שגיאה באיפוס סיסמה: {str(e)}")
            return False, str(e)
    
    def check_free_session_limit(self, user_id):
        """בדיקת מגבלת סשנים חינמיים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT free_sessions_used, free_sessions_limit, subscription_type, payment_status
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                free_sessions_used, free_sessions_limit, subscription_type, payment_status = result
                
                # וידוא שהערכים לא null
                if free_sessions_used is None:
                    free_sessions_used = 0
                if free_sessions_limit is None:
                    free_sessions_limit = self.free_max_sessions
                
                print(f"🔍 בדיקת מגבלת סשנים עבור משתמש {user_id}: {free_sessions_used}/{free_sessions_limit}")
                
                # מנוי בתשלום = ללא הגבלה
                if subscription_type in ['premium', 'professional'] and payment_status == 'paid':
                    print(f"✅ מנוי בתשלום - ללא הגבלה")
                    return True, free_sessions_used, -1, 'paid'
                
                # בדיקת מגבלת סשנים חינמיים - רק אם באמת הגיע למגבלה
                if free_sessions_used >= free_sessions_limit:
                    print(f"❌ הגיע למגבלת סשנים: {free_sessions_used} >= {free_sessions_limit}")
                    return False, free_sessions_used, free_sessions_limit, 'limit_reached'
                
                print(f"✅ יש עוד סשנים זמינים: {free_sessions_limit - free_sessions_used}")
                return True, free_sessions_used, free_sessions_limit, 'trial'
            
            print(f"❌ לא נמצא משתמש {user_id}")
            return False, 0, 0, 'error'
            
        except Exception as e:
            print(f"❌ שגיאה בבדיקת מגבלת סשנים חינמיים: {str(e)}")
            return False, 0, 0, 'error'
    
    def check_free_patient_limit(self, user_id):
        """בדיקת מגבלת מטופלים חינמיים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT subscription_type, payment_status
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                subscription_type, payment_status = result
                
                # מנוי בתשלום = ללא הגבלה
                if subscription_type in ['premium', 'professional'] and payment_status == 'paid':
                    return True, -1, -1, 'paid'
                
                # מנוי חינמי = מטופלים מוגבלים לפי משתנה הסביבה
                # נספור כמה מטופלים יש כרגע (תיקיות בתיקיית transcripts)
                import os
                transcripts_folder = 'transcripts'
                current_patients = 0
                
                if os.path.exists(transcripts_folder):
                    user_folder = os.path.join(transcripts_folder, f'user_{user_id}')
                    if os.path.exists(user_folder):
                        # ספירת תיקיות מטופלים בלבד (לא קבצים)
                        for item in os.listdir(user_folder):
                            item_path = os.path.join(user_folder, item)
                            if os.path.isdir(item_path):
                                current_patients += 1
                
                # מגבלה ממשתנה הסביבה
                max_patients = self.free_max_patients
                
                # תמיד מאפשר ליצור מטופל ראשון
                if current_patients < max_patients:
                    return True, current_patients, max_patients, 'trial'
                else:
                    return False, current_patients, max_patients, 'limit_reached'
            
            # אם אין נתונים - מאפשר יצירה (ברירת מחדל)
            return True, 0, self.free_max_patients, 'trial'
            
        except Exception as e:
            print(f"❌ שגיאה בבדיקת מגבלת מטופלים: {str(e)}")
            # במקרה של שגיאה - מאפשר יצירה
            return True, 0, self.free_max_patients, 'trial'
    
    def decrement_free_session(self, user_id):
        """הפחתת מונה סשנים חינמיים (כאשר מוחקים סשן)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET free_sessions_used = MAX(0, free_sessions_used - 1) WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בהפחתת מונה סשנים חינמיים: {str(e)}")
            return False
    
    def increment_free_session(self, user_id):
        """הגדלת מונה סשנים חינמיים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET free_sessions_used = free_sessions_used + 1 WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בעדכון מונה סשנים חינמיים: {str(e)}")
            return False
    
    def reset_free_sessions_counter(self, user_id):
        """איפוס מונה סשנים חינמיים (לפתרון בעיות)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET free_sessions_used = 0 WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ מונה סשנים חינמיים אופס עבור משתמש {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה באיפוס מונה סשנים חינמיים: {str(e)}")
            return False
    
    def upgrade_to_premium(self, user_id, payment_method='manual'):
        """שדרוג למנוי פרימיום"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # עדכון סטטוס המנוי
            cursor.execute('''
                UPDATE users SET 
                    subscription_type = 'premium',
                    payment_status = 'paid',
                    subscription_expires = ?
                WHERE id = ?
            ''', ((datetime.datetime.now() + datetime.timedelta(days=365)).isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ משתמש {user_id} שודרג למנוי פרימיום")
            return True, 'שודרג למנוי פרימיום בהצלחה'
            
        except Exception as e:
            print(f"❌ שגיאה בשדרוג למנוי פרימיום: {str(e)}")
            return False, str(e)
    
    def get_subscription_status(self, user_id):
        """קבלת סטטוס מנוי"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT subscription_type, payment_status, subscription_expires, 
                       free_sessions_used, free_sessions_limit
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                subscription_type, payment_status, subscription_expires, free_sessions_used, free_sessions_limit = result
                
                # בדיקת תוקף מנוי
                is_expired = False
                if subscription_expires:
                    expires_date = datetime.datetime.fromisoformat(subscription_expires)
                    is_expired = expires_date < datetime.datetime.now()
                
                return {
                    'subscription_type': subscription_type,
                    'payment_status': payment_status,
                    'subscription_expires': subscription_expires,
                    'is_expired': is_expired,
                    'free_sessions_used': free_sessions_used,
                    'free_sessions_limit': free_sessions_limit,
                    'sessions_remaining': max(0, free_sessions_limit - free_sessions_used) if subscription_type == 'trial' else -1,
                    'max_patients_allowed': self.free_max_patients if subscription_type == 'trial' else -1
                }
            
            return None
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת סטטוס מנוי: {str(e)}")
            return None
    
    def create_payment_session(self, user_id, plan_type='premium'):
        """יצירת סשן תשלום (המה - לשילוב עם מערכת תשלומים אמיתית)"""
        try:
            # כאן תוכל לשלב עם מערכת תשלומים אמיתית כמו Stripe, PayPal וכו'
            payment_session_id = secrets.token_urlsafe(32)
            
            # שמירת פרטי התשלום בבסיס הנתונים
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # יצירת טבלת תשלומים אם לא קיימת
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT UNIQUE,
                    plan_type TEXT,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # הגדרת מחיר לפי תוכנית
            amount = 99.0 if plan_type == 'premium' else 199.0  # מחירים לדוגמה
            
            cursor.execute('''
                INSERT INTO payment_sessions (user_id, session_id, plan_type, amount)
                VALUES (?, ?, ?, ?)
            ''', (user_id, payment_session_id, plan_type, amount))
            
            conn.commit()
            conn.close()
            
            return True, {
                'payment_session_id': payment_session_id,
                'amount': amount,
                'plan_type': plan_type,
                'payment_url': f'/payment/{payment_session_id}'  # URL לדף התשלום
            }
            
        except Exception as e:
            print(f"❌ שגיאה ביצירת סשן תשלום: {str(e)}")
            return False, str(e)
    
    def complete_payment(self, payment_session_id, payment_method='manual'):
        """השלמת תשלום"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # קבלת פרטי התשלום
            cursor.execute('''
                SELECT user_id, plan_type, status FROM payment_sessions 
                WHERE session_id = ?
            ''', (payment_session_id,))
            
            result = cursor.fetchone()
            if not result:
                return False, 'סשן תשלום לא נמצא'
            
            user_id, plan_type, status = result
            
            if status == 'completed':
                return False, 'התשלום כבר הושלם'
            
            # עדכון סטטוס התשלום
            cursor.execute('''
                UPDATE payment_sessions SET 
                    status = 'completed',
                    completed_at = ?
                WHERE session_id = ?
            ''', (datetime.datetime.now().isoformat(), payment_session_id))
            
            # שדרוג המשתמש
            if plan_type == 'premium':
                cursor.execute('''
                    UPDATE users SET 
                        subscription_type = 'premium',
                        payment_status = 'paid',
                        subscription_expires = ?
                    WHERE id = ?
                ''', ((datetime.datetime.now() + datetime.timedelta(days=365)).isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ תשלום הושלם עבור משתמש {user_id}")
            return True, 'התשלום הושלם בהצלחה'
            
        except Exception as e:
            print(f"❌ שגיאה בהשלמת תשלום: {str(e)}")
            return False, str(e)
    
    def get_all_users(self):
        """קבלת רשימת כל המשתמשים (למנהלים)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, full_name, subscription_type, subscription_expires, 
                       usage_count, usage_limit, created_at, last_login, is_active,
                       free_sessions_used, free_sessions_limit, payment_status
                FROM users
                ORDER BY created_at DESC
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'email': row[1],
                    'full_name': row[2],
                    'subscription_type': row[3],
                    'subscription_expires': row[4],
                    'usage_count': row[5],
                    'usage_limit': row[6],
                    'created_at': row[7],
                    'last_login': row[8],
                    'is_active': bool(row[9]),
                    'free_sessions_used': row[10],
                    'free_sessions_limit': row[11],
                    'payment_status': row[12]
                })
            
            conn.close()
            return users
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת רשימת משתמשים: {str(e)}")
            return []

def require_auth(f):
    """דקורטור להרישת אימות - מחזיר JSON error"""
    from functools import wraps
    from flask import jsonify, request
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_manager = AuthManager()
        
        # בדיקת session token
        session_token = request.headers.get('Authorization')
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]
        else:
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({'error': 'נדרש אימות'}), 401
        
        is_valid, user_data = auth_manager.verify_session(session_token)
        if not is_valid:
            return jsonify({'error': 'Session לא תקין'}), 401
        
        # בדיקת מגבלת שימוש
        can_use, usage_count, usage_limit = auth_manager.check_usage_limit(user_data['user_id'])
        if not can_use:
            return jsonify({
                'error': 'הגעת למגבלת השימוש החודשית',
                'usage_count': usage_count,
                'usage_limit': usage_limit
            }), 429
        
        # הוספת מידע המשתמש לבקשה
        request.current_user = user_data
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_auth_html(f):
    """דקורטור להרישת אימות לדפי HTML - מפנה לדף כניסה"""
    from functools import wraps
    from flask import redirect, request, render_template
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_manager = AuthManager()
        
        # בדיקת session token
        session_token = request.headers.get('Authorization')
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]
        else:
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            # הפניה לדף כניסה במקום JSON error
            return redirect('/login')
        
        is_valid, user_data = auth_manager.verify_session(session_token)
        if not is_valid:
            # הפניה לדף כניסה במקום JSON error
            return redirect('/login')
        
        # בדיקת מגבלת שימוש
        can_use, usage_count, usage_limit = auth_manager.check_usage_limit(user_data['user_id'])
        if not can_use:
            # הצגת דף שגיאה במקום JSON
            return render_template('error.html', 
                                 error_title='הגעת למגבלת השימוש',
                                 error_message=f'הגעת למגבלת השימוש החודשית ({usage_count}/{usage_limit})',
                                 show_upgrade=True), 429
        
        # הוספת מידע המשתמש לבקשה
        request.current_user = user_data
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_session_limit_check(f):
    """דקורטור לבדיקת מגבלת סשנים חינמיים"""
    from functools import wraps
    from flask import jsonify, request
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_manager = AuthManager()
        
        # בדיקת session token
        session_token = request.headers.get('Authorization')
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]
        else:
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({'error': 'נדרש אימות'}), 401
        
        is_valid, user_data = auth_manager.verify_session(session_token)
        if not is_valid:
            return jsonify({'error': 'Session לא תקין'}), 401
        
        # בדיקת מגבלת סשנים חינמיים
        can_create, sessions_used, sessions_limit, status = auth_manager.check_free_session_limit(user_data['user_id'])
        
        if not can_create and status == 'limit_reached':
            return jsonify({
                'error': 'הגעת למגבלת הסשנים החינמיים',
                'message': 'כדי להמשיך להשתמש במערכת, יש לשדרג למנוי בתשלום',
                'sessions_used': sessions_used,
                'sessions_limit': sessions_limit,
                'subscription_required': True,
                'upgrade_url': '/subscription/upgrade'
            }), 402  # Payment Required
        
        # הוספת מידע המשתמש לבקשה
        request.current_user = user_data
        request.session_status = {
            'can_create': can_create,
            'sessions_used': sessions_used,
            'sessions_limit': sessions_limit,
            'status': status
        }
        
        return f(*args, **kwargs)
    
    return decorated_function
