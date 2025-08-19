# encryption_manager.py - מנהל הצפנה דו-שכבתית למערכת היברידית
import os
import json
import base64
import hashlib
import secrets
import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import sqlite3
from dotenv import load_dotenv

load_dotenv()

class EncryptionManager:
    """מנהל הצפנה דו-שכבתית - הצפנה מקומית + סנכרון מוצפן"""
    
    def __init__(self):
        self.db_path = 'encryption_keys.db'
        self.init_database()
    
    def init_database(self):
        """יצירת מסד נתונים למפתחות הצפנה"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # טבלת מפתחות הצפנה אישיים של מטפלים
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_encryption_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                key_verification TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT
            )
        ''')
        
        # טבלת סשנים מוצפנים בענן
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encrypted_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT UNIQUE NOT NULL,
                patient_name_hash TEXT NOT NULL,
                session_date TEXT NOT NULL,
                encrypted_data TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'synced'
            )
        ''')
        
        # טבלת מטא-דאטה לסנכרון
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                last_sync TEXT,
                sync_version INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("🔐 מסד נתונים הצפנה מוכן")
    
    def generate_user_encryption_key(self, user_id, master_password):
        """יצירת מפתח הצפנה אישי למטפל"""
        try:
            # יצירת salt ייחודי
            salt = os.urandom(32)  # 256 bits
            
            # יצירת מפתח חזק עם Scrypt (עמיד יותר מ-PBKDF2)
            kdf = Scrypt(
                length=32,
                salt=salt,
                n=2**14,  # 16384 iterations
                r=8,
                p=1,
            )
            
            # גזירת מפתח מהסיסמה האישית
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode('utf-8')))
            
            # יצירת אימות למפתח (לבדיקה שהסיסמה נכונה)
            verification_data = "ENCRYPTION_KEY_VERIFICATION_" + str(user_id)
            fernet = Fernet(key)
            key_verification = fernet.encrypt(verification_data.encode('utf-8')).decode('utf-8')
            
            # שמירה במסד הנתונים
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_encryption_keys 
                (user_id, salt, key_verification, last_used)
                VALUES (?, ?, ?, ?)
            ''', (user_id, base64.b64encode(salt).decode('utf-8'), 
                  key_verification, datetime.datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            print(f"🔑 מפתח הצפנה אישי נוצר למטפל {user_id}")
            return True, key.decode('utf-8')
            
        except Exception as e:
            print(f"❌ שגיאה ביצירת מפתח הצפנה: {str(e)}")
            return False, str(e)
    
    def verify_user_password(self, user_id, master_password):
        """אימות סיסמת הצפנה של המטפל"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT salt, key_verification FROM user_encryption_keys 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, "לא נמצא מפתח הצפנה למטפל זה"
            
            salt_b64, key_verification = result
            salt = base64.b64decode(salt_b64.encode('utf-8'))
            
            # שחזור המפתח מהסיסמה
            kdf = Scrypt(
                length=32,
                salt=salt,
                n=2**14,
                r=8,
                p=1,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode('utf-8')))
            
            # בדיקת נכונות המפתח
            try:
                fernet = Fernet(key)
                verification_data = fernet.decrypt(key_verification.encode('utf-8')).decode('utf-8')
                expected_data = "ENCRYPTION_KEY_VERIFICATION_" + str(user_id)
                
                if verification_data == expected_data:
                    # עדכון זמן שימוש אחרון
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE user_encryption_keys SET last_used = ? WHERE user_id = ?
                    ''', (datetime.datetime.now().isoformat(), user_id))
                    conn.commit()
                    conn.close()
                    
                    return True, key.decode('utf-8')
                else:
                    return False, "סיסמת הצפנה שגויה"
                    
            except Exception:
                return False, "סיסמת הצפנה שגויה"
                
        except Exception as e:
            print(f"❌ שגיאה באימות סיסמת הצפנה: {str(e)}")
            return False, str(e)
    
    def encrypt_session_data(self, user_id, session_data, encryption_key):
        """הצפנת נתוני סשן לפני שמירה/סנכרון"""
        try:
            # המרת נתוני הסשן ל-JSON
            session_json = json.dumps(session_data, ensure_ascii=False, indent=2)
            
            # הצפנה עם המפתח האישי
            fernet = Fernet(encryption_key.encode('utf-8'))
            encrypted_data = fernet.encrypt(session_json.encode('utf-8'))
            
            # יצירת hash של שם המטופל (לחיפוש ללא פענוח)
            patient_name = session_data.get('patient_name', '')
            patient_hash = hashlib.sha256(f"{user_id}_{patient_name}".encode('utf-8')).hexdigest()
            
            # יצירת מזהה ייחודי לסשן
            session_id = hashlib.sha256(
                f"{user_id}_{patient_name}_{session_data.get('session_date', '')}_{datetime.datetime.now().isoformat()}"
                .encode('utf-8')
            ).hexdigest()
            
            # מטא-דאטה לא מוצפנת (לחיפוש ומיון)
            metadata = {
                'word_count': session_data.get('word_count', 0),
                'audio_filename': session_data.get('audio_filename', ''),
                'quality_mode': session_data.get('quality_mode', ''),
                'created_at': session_data.get('created_at', datetime.datetime.now().isoformat())
            }
            
            print(f"🔐 סשן הוצפן בהצלחה: {session_id[:8]}...")
            return True, {
                'session_id': session_id,
                'patient_name_hash': patient_hash,
                'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
                'metadata': json.dumps(metadata, ensure_ascii=False)
            }
            
        except Exception as e:
            print(f"❌ שגיאה בהצפנת סשן: {str(e)}")
            return False, str(e)
    
    def decrypt_session_data(self, encrypted_session, encryption_key):
        """פענוח נתוני סשן"""
        try:
            # פענוח הנתונים
            encrypted_data = base64.b64decode(encrypted_session['encrypted_data'].encode('utf-8'))
            fernet = Fernet(encryption_key.encode('utf-8'))
            decrypted_json = fernet.decrypt(encrypted_data).decode('utf-8')
            
            # המרה חזרה ל-dict
            session_data = json.loads(decrypted_json)
            
            # הוספת מטא-דאטה
            if 'metadata' in encrypted_session:
                metadata = json.loads(encrypted_session['metadata'])
                session_data.update(metadata)
            
            print(f"🔓 סשן פוענח בהצלחה")
            return True, session_data
            
        except Exception as e:
            print(f"❌ שגיאה בפענוח סשן: {str(e)}")
            return False, str(e)
    
    def save_encrypted_session(self, user_id, encrypted_session_data, session_date):
        """שמירת סשן מוצפן במסד הנתונים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO encrypted_sessions 
                (user_id, session_id, patient_name_hash, session_date, 
                 encrypted_data, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                encrypted_session_data['session_id'],
                encrypted_session_data['patient_name_hash'],
                session_date,
                encrypted_session_data['encrypted_data'],
                encrypted_session_data['metadata'],
                datetime.datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            print(f"💾 סשן מוצפן נשמר בענן למטפל {user_id}")
            return True, encrypted_session_data['session_id']
            
        except Exception as e:
            print(f"❌ שגיאה בשמירת סשן מוצפן: {str(e)}")
            return False, str(e)
    
    def get_user_encrypted_sessions(self, user_id, patient_name_filter=None):
        """קבלת כל הסשנים המוצפנים של מטפל"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if patient_name_filter:
                # חיפוש לפי hash של שם המטופל
                patient_hash = hashlib.sha256(f"{user_id}_{patient_name_filter}".encode('utf-8')).hexdigest()
                cursor.execute('''
                    SELECT session_id, patient_name_hash, session_date, 
                           encrypted_data, metadata, created_at, updated_at
                    FROM encrypted_sessions 
                    WHERE user_id = ? AND patient_name_hash = ?
                    ORDER BY session_date DESC, created_at DESC
                ''', (user_id, patient_hash))
            else:
                cursor.execute('''
                    SELECT session_id, patient_name_hash, session_date, 
                           encrypted_data, metadata, created_at, updated_at
                    FROM encrypted_sessions 
                    WHERE user_id = ?
                    ORDER BY session_date DESC, created_at DESC
                ''', (user_id,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'patient_name_hash': row[1],
                    'session_date': row[2],
                    'encrypted_data': row[3],
                    'metadata': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            
            conn.close()
            
            print(f"📋 נמצאו {len(sessions)} סשנים מוצפנים למטפל {user_id}")
            return True, sessions
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת סשנים מוצפנים: {str(e)}")
            return False, str(e)
    
    def delete_encrypted_session(self, user_id, session_id):
        """מחיקת סשן מוצפן"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM encrypted_sessions 
                WHERE user_id = ? AND session_id = ?
            ''', (user_id, session_id))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                print(f"🗑️ סשן מוצפן נמחק: {session_id[:8]}...")
                return True, "סשן נמחק בהצלחה"
            else:
                return False, "סשן לא נמצא"
                
        except Exception as e:
            print(f"❌ שגיאה במחיקת סשן מוצפן: {str(e)}")
            return False, str(e)
    
    def sync_sessions_to_cloud(self, user_id, encryption_key):
        """סנכרון סשנים מוצפנים לענן (מדמה - בעתיד יהיה API אמיתי)"""
        try:
            # בעתיד כאן יהיה קוד לסנכרון עם שרת ענן אמיתי
            # לעת עתה נשמור במסד הנתונים המקומי
            
            success, sessions = self.get_user_encrypted_sessions(user_id)
            if not success:
                return False, "שגיאה בקבלת סשנים לסנכרון"
            
            # עדכון סטטוס סנכרון
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sync_metadata 
                (user_id, device_id, last_sync, sync_version)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                self.get_device_id(),
                datetime.datetime.now().isoformat(),
                1
            ))
            
            conn.commit()
            conn.close()
            
            print(f"☁️ סנכרון הושלם למטפל {user_id} - {len(sessions)} סשנים")
            return True, f"סונכרנו {len(sessions)} סשנים"
            
        except Exception as e:
            print(f"❌ שגיאה בסנכרון לענן: {str(e)}")
            return False, str(e)
    
    def get_device_id(self):
        """יצירת מזהה ייחודי למכשיר"""
        try:
            import platform
            import uuid
            
            # יצירת מזהה בסיס על המכשיר
            device_info = f"{platform.system()}_{platform.node()}_{uuid.getnode()}"
            device_id = hashlib.sha256(device_info.encode('utf-8')).hexdigest()[:16]
            
            return device_id
            
        except Exception:
            # גיבוי - מזהה אקראי
            return secrets.token_hex(8)
    
    def export_encrypted_backup(self, user_id, encryption_key):
        """יצוא גיבוי מוצפן של כל הסשנים"""
        try:
            success, sessions = self.get_user_encrypted_sessions(user_id)
            if not success:
                return False, "שגיאה בקבלת סשנים לגיבוי"
            
            # יצירת מבנה גיבוי
            backup_data = {
                'user_id': user_id,
                'export_date': datetime.datetime.now().isoformat(),
                'device_id': self.get_device_id(),
                'sessions_count': len(sessions),
                'sessions': sessions,
                'version': '1.0'
            }
            
            # הצפנה נוספת של כל הגיבוי
            backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
            fernet = Fernet(encryption_key.encode('utf-8'))
            encrypted_backup = fernet.encrypt(backup_json.encode('utf-8'))
            
            # קידוד Base64 לשמירה
            backup_b64 = base64.b64encode(encrypted_backup).decode('utf-8')
            
            print(f"📦 גיבוי מוצפן נוצר למטפל {user_id} - {len(sessions)} סשנים")
            return True, backup_b64
            
        except Exception as e:
            print(f"❌ שגיאה ביצירת גיבוי מוצפן: {str(e)}")
            return False, str(e)
    
    def import_encrypted_backup(self, user_id, backup_data, encryption_key):
        """יבוא גיבוי מוצפן"""
        try:
            # פענוח הגיבוי
            encrypted_backup = base64.b64decode(backup_data.encode('utf-8'))
            fernet = Fernet(encryption_key.encode('utf-8'))
            backup_json = fernet.decrypt(encrypted_backup).decode('utf-8')
            backup = json.loads(backup_json)
            
            # בדיקת תקינות הגיבוי
            if backup.get('user_id') != user_id:
                return False, "הגיבוי לא שייך למטפל זה"
            
            sessions = backup.get('sessions', [])
            imported_count = 0
            
            # יבוא כל הסשנים
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for session in sessions:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO encrypted_sessions 
                        (user_id, session_id, patient_name_hash, session_date, 
                         encrypted_data, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        session['session_id'],
                        session['patient_name_hash'],
                        session['session_date'],
                        session['encrypted_data'],
                        session['metadata'],
                        session['created_at'],
                        session['updated_at']
                    ))
                    imported_count += 1
                except Exception as e:
                    print(f"⚠️ שגיאה ביבוא סשן {session.get('session_id', 'unknown')}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            print(f"📥 גיבוי יובא בהצלחה למטפל {user_id} - {imported_count} סשנים")
            return True, f"יובאו {imported_count} סשנים מתוך {len(sessions)}"
            
        except Exception as e:
            print(f"❌ שגיאה ביבוא גיבוי מוצפן: {str(e)}")
            return False, str(e)
    
    def get_encryption_stats(self, user_id):
        """סטטיסטיקות הצפנה למטפל"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # מספר סשנים מוצפנים
            cursor.execute('''
                SELECT COUNT(*) FROM encrypted_sessions WHERE user_id = ?
            ''', (user_id,))
            sessions_count = cursor.fetchone()[0]
            
            # תאריך יצירת מפתח הצפנה
            cursor.execute('''
                SELECT created_at, last_used FROM user_encryption_keys WHERE user_id = ?
            ''', (user_id,))
            key_info = cursor.fetchone()
            
            # תאריך סנכרון אחרון
            cursor.execute('''
                SELECT last_sync, sync_version FROM sync_metadata WHERE user_id = ?
            ''', (user_id,))
            sync_info = cursor.fetchone()
            
            conn.close()
            
            stats = {
                'encrypted_sessions_count': sessions_count,
                'encryption_key_created': key_info[0] if key_info else None,
                'encryption_key_last_used': key_info[1] if key_info else None,
                'last_sync': sync_info[0] if sync_info else None,
                'sync_version': sync_info[1] if sync_info else 0,
                'device_id': self.get_device_id()
            }
            
            return True, stats
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת סטטיסטיקות הצפנה: {str(e)}")
            return False, str(e)
