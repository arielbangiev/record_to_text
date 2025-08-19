#!/usr/bin/env python3
# user_management.py - כלי לניהול משתמשים
import sqlite3
import bcrypt
import datetime
import secrets
from auth_manager import AuthManager

class UserManagement:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.db_path = 'users.db'
    
    def list_users(self):
        """הצגת כל המשתמשים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, full_name, subscription_type, subscription_expires, 
                       created_at, last_login, is_active, free_sessions_used, free_sessions_limit
                FROM users
                ORDER BY created_at DESC
            ''')
            
            users = cursor.fetchall()
            conn.close()
            
            print("\n=== רשימת משתמשים ===")
            print(f"{'ID':<3} {'אימייל':<30} {'שם מלא':<20} {'מנוי':<10} {'פעיל':<5} {'סשנים':<10}")
            print("-" * 80)
            
            for user in users:
                user_id, email, full_name, sub_type, sub_expires, created_at, last_login, is_active, sessions_used, sessions_limit = user
                active_status = "✅" if is_active else "❌"
                sessions_info = f"{sessions_used}/{sessions_limit}"
                
                print(f"{user_id:<3} {email:<30} {full_name:<20} {sub_type:<10} {active_status:<5} {sessions_info:<10}")
            
            return users
            
        except Exception as e:
            print(f"❌ שגיאה בהצגת משתמשים: {str(e)}")
            return []
    
    def list_sessions(self):
        """הצגת כל הסשנים הפעילים"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.id, s.user_id, u.email, s.session_token, s.expires_at, s.created_at
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.expires_at > ?
                ORDER BY s.created_at DESC
            ''', (datetime.datetime.now().isoformat(),))
            
            sessions = cursor.fetchall()
            conn.close()
            
            print("\n=== סשנים פעילים ===")
            print(f"{'ID':<3} {'משתמש':<30} {'טוקן':<20} {'פג תוקף':<20}")
            print("-" * 75)
            
            for session in sessions:
                session_id, user_id, email, token, expires_at, created_at = session
                token_short = token[:16] + "..."
                expires_short = expires_at[:16]
                
                print(f"{session_id:<3} {email:<30} {token_short:<20} {expires_short:<20}")
            
            return sessions
            
        except Exception as e:
            print(f"❌ שגיאה בהצגת סשנים: {str(e)}")
            return []
    
    def create_user(self, email, password, full_name):
        """יצירת משתמש חדש"""
        try:
            success, result = self.auth_manager.register_user(email, password, full_name)
            if success:
                print(f"✅ משתמש חדש נוצר בהצלחה: {email}")
                return True
            else:
                print(f"❌ שגיאה ביצירת משתמש: {result}")
                return False
        except Exception as e:
            print(f"❌ שגיאה ביצירת משתמש: {str(e)}")
            return False
    
    def delete_user(self, user_id):
        """מחיקת משתמש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # קבלת פרטי המשתמש לפני המחיקה
            cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ משתמש עם ID {user_id} לא נמצא")
                return False
            
            email = user[0]
            
            # מחיקת הסשנים של המשתמש
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            
            # מחיקת המשתמש
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ משתמש {email} נמחק בהצלחה")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה במחיקת משתמש: {str(e)}")
            return False
    
    def reset_user_password(self, email, new_password):
        """איפוס סיסמת משתמש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # בדיקה אם המשתמש קיים
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ משתמש עם אימייל {email} לא נמצא")
                return False
            
            # הצפנת הסיסמה החדשה
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # עדכון הסיסמה
            cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
            
            conn.commit()
            conn.close()
            
            print(f"✅ סיסמה אופסה בהצלחה עבור {email}")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה באיפוס סיסמה: {str(e)}")
            return False
    
    def activate_user(self, user_id):
        """הפעלת משתמש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
            
            if cursor.rowcount == 0:
                print(f"❌ משתמש עם ID {user_id} לא נמצא")
                return False
            
            conn.commit()
            conn.close()
            
            print(f"✅ משתמש {user_id} הופעל בהצלחה")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בהפעלת משתמש: {str(e)}")
            return False
    
    def deactivate_user(self, user_id):
        """השבתת משתמש"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            
            if cursor.rowcount == 0:
                print(f"❌ משתמש עם ID {user_id} לא נמצא")
                return False
            
            # מחיקת כל הסשנים של המשתמש
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ משתמש {user_id} הושבת בהצלחה")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בהשבתת משתמש: {str(e)}")
            return False
    
    def clear_expired_sessions(self):
        """ניקוי סשנים שפג תוקפם"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM sessions WHERE expires_at < ?', (datetime.datetime.now().isoformat(),))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"✅ נוקו {deleted_count} סשנים שפג תוקפם")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בניקוי סשנים: {str(e)}")
            return False
    
    def test_login(self, email, password):
        """בדיקת התחברות"""
        try:
            print(f"🔍 בודק התחברות עבור: {email}")
            
            success, result = self.auth_manager.login_user(email, password)
            
            if success:
                print(f"✅ התחברות בהצלחה!")
                print(f"   טוקן: {result['session_token'][:20]}...")
                print(f"   שם מלא: {result['full_name']}")
                return True, result
            else:
                print(f"❌ התחברות נכשלה: {result}")
                return False, result
                
        except Exception as e:
            print(f"❌ שגיאה בבדיקת התחברות: {str(e)}")
            return False, str(e)

def main():
    """תפריט ראשי"""
    um = UserManagement()
    
    while True:
        print("\n" + "="*50)
        print("🔧 כלי ניהול משתמשים")
        print("="*50)
        print("1. הצגת כל המשתמשים")
        print("2. הצגת סשנים פעילים")
        print("3. יצירת משתמש חדש")
        print("4. מחיקת משתמש")
        print("5. איפוס סיסמת משתמש")
        print("6. הפעלת משתמש")
        print("7. השבתת משתמש")
        print("8. ניקוי סשנים שפג תוקפם")
        print("9. בדיקת התחברות")
        print("0. יציאה")
        print("-"*50)
        
        choice = input("בחר אפשרות (0-9): ").strip()
        
        if choice == '1':
            um.list_users()
            
        elif choice == '2':
            um.list_sessions()
            
        elif choice == '3':
            email = input("אימייל: ").strip()
            password = input("סיסמה: ").strip()
            full_name = input("שם מלא: ").strip()
            um.create_user(email, password, full_name)
            
        elif choice == '4':
            um.list_users()
            user_id = input("הזן ID של המשתמש למחיקה: ").strip()
            if user_id.isdigit():
                um.delete_user(int(user_id))
            else:
                print("❌ ID לא תקין")
                
        elif choice == '5':
            email = input("אימייל המשתמש: ").strip()
            new_password = input("סיסמה חדשה: ").strip()
            um.reset_user_password(email, new_password)
            
        elif choice == '6':
            um.list_users()
            user_id = input("הזן ID של המשתמש להפעלה: ").strip()
            if user_id.isdigit():
                um.activate_user(int(user_id))
            else:
                print("❌ ID לא תקין")
                
        elif choice == '7':
            um.list_users()
            user_id = input("הזן ID של המשתמש להשבתה: ").strip()
            if user_id.isdigit():
                um.deactivate_user(int(user_id))
            else:
                print("❌ ID לא תקין")
                
        elif choice == '8':
            um.clear_expired_sessions()
            
        elif choice == '9':
            email = input("אימייל: ").strip()
            password = input("סיסמה: ").strip()
            um.test_login(email, password)
            
        elif choice == '0':
            print("👋 להתראות!")
            break
            
        else:
            print("❌ אפשרות לא תקינה")
        
        input("\nלחץ Enter להמשך...")

if __name__ == "__main__":
    main()
