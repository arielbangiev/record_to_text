# cloud_sync_manager.py - מנהל סנכרון מאובטח בין מכשירים
import os
import json
import hashlib
import secrets
import datetime
import requests
import sqlite3
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from auth_manager import AuthManager
from encryption_manager import EncryptionManager

load_dotenv()

class CloudSyncManager:
    """מנהל סנכרון מאובטח בין מכשירים עם הצפנה מלאה"""
    
    def __init__(self):
        self.db_path = 'cloud_sync.db'
        self.sync_server_url = os.getenv('SYNC_SERVER_URL', 'https://your-sync-server.com/api')
        self.sync_api_key = os.getenv('SYNC_API_KEY', '')
        self.encryption_manager = EncryptionManager()
        self.auth_manager = AuthManager()
        self.init_database()
    
    def init_database(self):
        """יצירת מסד נתונים לסנכרון"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # טבלת מכשירים מורשים למטפל
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authorized_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                device_name TEXT,
                device_type TEXT,
                public_key TEXT,
                authorized_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_sync TEXT,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(user_id, device_id)
            )
        ''')
        
        # טבלת סשנים מסונכרנים
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS synced_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                patient_name_hash TEXT NOT NULL,
                session_date TEXT NOT NULL,
                encrypted_data TEXT NOT NULL,
                metadata TEXT,
                device_origin TEXT,
                cloud_hash TEXT,
                last_modified TEXT,
                sync_status TEXT DEFAULT 'pending',
                conflict_resolution TEXT,
                UNIQUE(user_id, session_id)
            )
        ''')
        
        # טבלת קונפליקטים בסנכרון
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                local_data TEXT,
                remote_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolution_action TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("🔄 מסד נתונים סנכרון מוכן")
    
    def get_device_id(self):
        """יצירת מזהה ייחודי למכשיר הנוכחי"""
        try:
            import platform
            import uuid
            
            # מידע על המכשיר
            system = platform.system()
            node = platform.node()
            mac = uuid.getnode()
            
            # יצירת מזהה יציב
            device_info = f"{system}_{node}_{mac}"
            device_id = hashlib.sha256(device_info.encode('utf-8')).hexdigest()[:16]
            
            return device_id
            
        except Exception:
            # גיבוי - מזהה אקראי (לא יציב!)
            return secrets.token_hex(8)
    
    def register_device(self, user_id, device_name=None, device_type=None):
        """רישום מכשיר חדש למטפל"""
        try:
            device_id = self.get_device_id()
            
            if not device_name:
                import platform
                device_name = f"{platform.system()} - {platform.node()}"
            
            if not device_type:
                import platform
                device_type = platform.system().lower()
            
            # יצירת מפתח ציבורי למכשיר (לעתיד - הצפנה אסימטרית)
            public_key = secrets.token_urlsafe(32)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO authorized_devices 
                (user_id, device_id, device_name, device_type, public_key, last_sync)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, device_id, device_name, device_type, public_key, 
                  datetime.datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            print(f"📱 מכשיר נרשם למטפל {user_id}: {device_name} ({device_id})")
            return True, {
                'device_id': device_id,
                'device_name': device_name,
                'device_type': device_type
            }
            
        except Exception as e:
            print(f"❌ שגיאה ברישום מכשיר: {str(e)}")
            return False, str(e)
    
    def get_user_devices(self, user_id):
        """קבלת רשימת מכשירים מורשים למטפל"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT device_id, device_name, device_type, authorized_at, 
                       last_sync, is_active
                FROM authorized_devices 
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_sync DESC
            ''', (user_id,))
            
            devices = []
            current_device_id = self.get_device_id()
            
            for row in cursor.fetchall():
                device_id, device_name, device_type, authorized_at, last_sync, is_active = row
                devices.append({
                    'device_id': device_id,
                    'device_name': device_name,
                    'device_type': device_type,
                    'authorized_at': authorized_at,
                    'last_sync': last_sync,
                    'is_current': device_id == current_device_id,
                    'is_active': bool(is_active)
                })
            
            conn.close()
            return True, devices
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת רשימת מכשירים: {str(e)}")
            return False, str(e)
    
    def sync_session_to_cloud(self, user_id, session_data, encryption_key):
        """סנכרון סשן בודד לענן"""
        try:
            # הצפנת הסשן
            success, encrypted_session = self.encryption_manager.encrypt_session_data(
                user_id, session_data, encryption_key
            )
            
            if not success:
                return False, f"שגיאה בהצפנה: {encrypted_session}"
            
            # יצירת hash לזיהוי שינויים
            data_hash = hashlib.sha256(
                encrypted_session['encrypted_data'].encode('utf-8')
            ).hexdigest()
            
            # שמירה במסד הנתונים המקומי
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO synced_sessions 
                (user_id, session_id, patient_name_hash, session_date, 
                 encrypted_data, metadata, device_origin, cloud_hash, 
                 last_modified, sync_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                encrypted_session['session_id'],
                encrypted_session['patient_name_hash'],
                session_data.get('session_date', ''),
                encrypted_session['encrypted_data'],
                encrypted_session['metadata'],
                self.get_device_id(),
                data_hash,
                datetime.datetime.now().isoformat(),
                'synced'
            ))
            
            conn.commit()
            conn.close()
            
            # סנכרון לשרת ענן (אם מוגדר)
            if self.sync_server_url and self.sync_api_key:
                cloud_success = self._upload_to_cloud_server(user_id, encrypted_session, data_hash)
                if not cloud_success:
                    print("⚠️ סנכרון לענן נכשל, נשמר מקומית")
            
            print(f"☁️ סשן סונכרן בהצלחה: {encrypted_session['session_id'][:8]}...")
            return True, encrypted_session['session_id']
            
        except Exception as e:
            print(f"❌ שגיאה בסנכרון סשן: {str(e)}")
            return False, str(e)
    
    def sync_all_sessions_to_cloud(self, user_id, encryption_key):
        """סנכרון כל הסשנים לענן"""
        try:
            # קבלת כל הסשנים המוצפנים
            success, sessions = self.encryption_manager.get_user_encrypted_sessions(user_id)
            if not success:
                return False, f"שגיאה בקבלת סשנים: {sessions}"
            
            synced_count = 0
            failed_count = 0
            
            for session in sessions:
                try:
                    # בדיקה אם הסשן כבר מסונכרן
                    if self._is_session_synced(user_id, session['session_id']):
                        continue
                    
                    # סנכרון הסשן
                    session_data = {
                        'session_id': session['session_id'],
                        'patient_name_hash': session['patient_name_hash'],
                        'session_date': session['session_date'],
                        'encrypted_data': session['encrypted_data'],
                        'metadata': session['metadata']
                    }
                    
                    success = self._sync_single_session(user_id, session_data)
                    if success:
                        synced_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    print(f"⚠️ שגיאה בסנכרון סשן {session.get('session_id', 'unknown')}: {str(e)}")
                    failed_count += 1
            
            print(f"☁️ סנכרון הושלם: {synced_count} הצליחו, {failed_count} נכשלו")
            return True, f"סונכרנו {synced_count} סשנים"
            
        except Exception as e:
            print(f"❌ שגיאה בסנכרון כללי: {str(e)}")
            return False, str(e)
    
    def sync_from_cloud(self, user_id, encryption_key):
        """סנכרון סשנים מהענן למכשיר הנוכחי"""
        try:
            # קבלת סשנים מהענן
            if self.sync_server_url and self.sync_api_key:
                cloud_sessions = self._download_from_cloud_server(user_id)
            else:
                # גיבוי - קבלה ממכשירים אחרים במסד הנתונים המקומי
                cloud_sessions = self._get_sessions_from_other_devices(user_id)
            
            if not cloud_sessions:
                return True, "אין סשנים חדשים לסנכרון"
            
            imported_count = 0
            conflict_count = 0
            
            for session in cloud_sessions:
                try:
                    # בדיקת קונפליקטים
                    if self._has_sync_conflict(user_id, session):
                        self._handle_sync_conflict(user_id, session)
                        conflict_count += 1
                        continue
                    
                    # יבוא הסשן
                    success = self._import_synced_session(user_id, session, encryption_key)
                    if success:
                        imported_count += 1
                        
                except Exception as e:
                    print(f"⚠️ שגיאה ביבוא סשן: {str(e)}")
            
            print(f"📥 יבוא הושלם: {imported_count} סשנים, {conflict_count} קונפליקטים")
            return True, f"יובאו {imported_count} סשנים חדשים"
            
        except Exception as e:
            print(f"❌ שגיאה בסנכרון מהענן: {str(e)}")
            return False, str(e)
    
    def get_sync_status(self, user_id):
        """קבלת סטטוס סנכרון"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # מספר סשנים מסונכרנים
            cursor.execute('''
                SELECT COUNT(*) FROM synced_sessions WHERE user_id = ?
            ''', (user_id,))
            synced_sessions = cursor.fetchone()[0]
            
            # מספר קונפליקטים פתוחים
            cursor.execute('''
                SELECT COUNT(*) FROM sync_conflicts WHERE user_id = ? AND resolved = 0
            ''', (user_id,))
            open_conflicts = cursor.fetchone()[0]
            
            # מכשירים פעילים
            cursor.execute('''
                SELECT COUNT(*) FROM authorized_devices WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            active_devices = cursor.fetchone()[0]
            
            # סנכרון אחרון
            cursor.execute('''
                SELECT MAX(last_sync) FROM authorized_devices WHERE user_id = ?
            ''', (user_id,))
            last_sync = cursor.fetchone()[0]
            
            conn.close()
            
            return True, {
                'synced_sessions': synced_sessions,
                'open_conflicts': open_conflicts,
                'active_devices': active_devices,
                'last_sync': last_sync,
                'current_device_id': self.get_device_id(),
                'sync_enabled': bool(self.sync_server_url and self.sync_api_key)
            }
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת סטטוס סנכרון: {str(e)}")
            return False, str(e)
    
    def resolve_sync_conflict(self, user_id, conflict_id, resolution_action):
        """פתרון קונפליקט סנכרון"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # קבלת פרטי הקונפליקט
            cursor.execute('''
                SELECT session_id, local_data, remote_data FROM sync_conflicts 
                WHERE id = ? AND user_id = ? AND resolved = 0
            ''', (conflict_id, user_id))
            
            conflict = cursor.fetchone()
            if not conflict:
                return False, "קונפליקט לא נמצא"
            
            session_id, local_data, remote_data = conflict
            
            # ביצוע הפתרון לפי הבחירה
            if resolution_action == 'keep_local':
                # שמירת הגרסה המקומית
                chosen_data = local_data
            elif resolution_action == 'keep_remote':
                # שמירת הגרסה המרוחקת
                chosen_data = remote_data
            elif resolution_action == 'merge':
                # מיזוג (מורכב - לעתיד)
                chosen_data = self._merge_session_data(local_data, remote_data)
            else:
                return False, "פעולת פתרון לא תקינה"
            
            # עדכון הסשן עם הנתונים הנבחרים
            session_data = json.loads(chosen_data)
            cursor.execute('''
                UPDATE synced_sessions SET 
                    encrypted_data = ?, 
                    last_modified = ?,
                    conflict_resolution = ?
                WHERE user_id = ? AND session_id = ?
            ''', (
                session_data['encrypted_data'],
                datetime.datetime.now().isoformat(),
                resolution_action,
                user_id,
                session_id
            ))
            
            # סימון הקונפליקט כפתור
            cursor.execute('''
                UPDATE sync_conflicts SET 
                    resolved = 1, 
                    resolution_action = ?
                WHERE id = ?
            ''', (resolution_action, conflict_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ קונפליקט נפתר: {session_id[:8]}... - {resolution_action}")
            return True, "קונפליקט נפתר בהצלחה"
            
        except Exception as e:
            print(f"❌ שגיאה בפתרון קונפליקט: {str(e)}")
            return False, str(e)
    
    def _is_session_synced(self, user_id, session_id):
        """בדיקה אם סשן כבר מסונכרן"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM synced_sessions 
                WHERE user_id = ? AND session_id = ?
            ''', (user_id, session_id))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception:
            return False
    
    def _sync_single_session(self, user_id, session_data):
        """סנכרון סשן בודד"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # יצירת hash
            data_hash = hashlib.sha256(
                session_data['encrypted_data'].encode('utf-8')
            ).hexdigest()
            
            cursor.execute('''
                INSERT OR REPLACE INTO synced_sessions 
                (user_id, session_id, patient_name_hash, session_date, 
                 encrypted_data, metadata, device_origin, cloud_hash, 
                 last_modified, sync_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                session_data['session_id'],
                session_data['patient_name_hash'],
                session_data['session_date'],
                session_data['encrypted_data'],
                session_data['metadata'],
                self.get_device_id(),
                data_hash,
                datetime.datetime.now().isoformat(),
                'synced'
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בסנכרון סשן בודד: {str(e)}")
            return False
    
    def _upload_to_cloud_server(self, user_id, encrypted_session, data_hash):
        """העלאה לשרת ענן (לעתיד)"""
        try:
            # כאן יהיה קוד לשליחה לשרת ענן אמיתי
            # לעת עתה נחזיר True (מדמה הצלחה)
            print(f"☁️ מדמה העלאה לענן: {encrypted_session['session_id'][:8]}...")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בהעלאה לענן: {str(e)}")
            return False
    
    def _download_from_cloud_server(self, user_id):
        """הורדה משרת ענן (לעתיד)"""
        try:
            # כאן יהיה קוד לקבלה משרת ענן אמיתי
            # לעת עתה נחזיר רשימה ריקה
            print(f"☁️ מדמה הורדה מהענן למטפל {user_id}...")
            return []
            
        except Exception as e:
            print(f"❌ שגיאה בהורדה מהענן: {str(e)}")
            return []
    
    def _get_sessions_from_other_devices(self, user_id):
        """קבלת סשנים ממכשירים אחרים (גיבוי מקומי)"""
        try:
            current_device = self.get_device_id()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_id, patient_name_hash, session_date, 
                       encrypted_data, metadata, device_origin
                FROM synced_sessions 
                WHERE user_id = ? AND device_origin != ?
            ''', (user_id, current_device))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'patient_name_hash': row[1],
                    'session_date': row[2],
                    'encrypted_data': row[3],
                    'metadata': row[4],
                    'device_origin': row[5]
                })
            
            conn.close()
            return sessions
            
        except Exception as e:
            print(f"❌ שגיאה בקבלה ממכשירים אחרים: {str(e)}")
            return []
    
    def _has_sync_conflict(self, user_id, session):
        """בדיקת קונפליקט סנכרון"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # בדיקה אם יש סשן עם אותו ID אבל נתונים שונים
            cursor.execute('''
                SELECT cloud_hash FROM synced_sessions 
                WHERE user_id = ? AND session_id = ?
            ''', (user_id, session['session_id']))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                existing_hash = result[0]
                new_hash = hashlib.sha256(session['encrypted_data'].encode('utf-8')).hexdigest()
                return existing_hash != new_hash
            
            return False
            
        except Exception:
            return False
    
    def _handle_sync_conflict(self, user_id, session):
        """טיפול בקונפליקט סנכרון"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # קבלת הנתונים המקומיים
            cursor.execute('''
                SELECT encrypted_data, metadata FROM synced_sessions 
                WHERE user_id = ? AND session_id = ?
            ''', (user_id, session['session_id']))
            
            local_result = cursor.fetchone()
            if local_result:
                local_data = json.dumps({
                    'encrypted_data': local_result[0],
                    'metadata': local_result[1]
                })
                
                remote_data = json.dumps({
                    'encrypted_data': session['encrypted_data'],
                    'metadata': session['metadata']
                })
                
                # שמירת הקונפליקט
                cursor.execute('''
                    INSERT INTO sync_conflicts 
                    (user_id, session_id, conflict_type, local_data, remote_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, session['session_id'], 'data_mismatch', local_data, remote_data))
                
                conn.commit()
            
            conn.close()
            print(f"⚠️ קונפליקט סנכרון נרשם: {session['session_id'][:8]}...")
            
        except Exception as e:
            print(f"❌ שגיאה בטיפול בקונפליקט: {str(e)}")
    
    def _import_synced_session(self, user_id, session, encryption_key):
        """יבוא סשן מסונכרן"""
        try:
            # פענוח הסשן לוודא תקינות
            success, decrypted_data = self.encryption_manager.decrypt_session_data(
                session, encryption_key
            )
            
            if not success:
                print(f"⚠️ לא ניתן לפענח סשן: {session['session_id'][:8]}...")
                return False
            
            # שמירה במסד הנתונים המקומי
            return self._sync_single_session(user_id, session)
            
        except Exception as e:
            print(f"❌ שגיאה ביבוא סשן: {str(e)}")
            return False
    
    def _merge_session_data(self, local_data, remote_data):
        """מיזוג נתוני סשן (פונקציה מתקדמת לעתיד)"""
        try:
            # לעת עתה נחזיר את הנתונים המקומיים
            # בעתיד כאן יהיה אלגוריתם מיזוג מתוחכם
            return local_data
            
        except Exception:
            return local_data
