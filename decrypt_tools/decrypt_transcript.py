#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט לפענוח תמלולים מוצפנים
שימוש: python decrypt_transcript.py <נתיב_לקובץ> <סיסמה>
"""

import sys
import json
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# הוספת התיקייה הראשית לנתיב
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def derive_key_from_password(password, salt=None):
    """גזירת מפתח הצפנה מסיסמה"""
    if salt is None:
        # אם אין salt, ננסה עם salt ברירת מחדל (כמו במערכת)
        salt = b'default_salt_for_transcript_encryption'
    
    # שימוש ב-PBKDF2 כמו במערכת המקורית
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
    return key

def decrypt_transcript_simple(encrypted_data, password):
    """פענוח פשוט של תמלול מוצפן"""
    try:
        # ניסיון פענוח עם מפתח שנגזר מהסיסמה
        key = derive_key_from_password(password)
        fernet = Fernet(key)
        
        # פענוח הנתונים
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        return True, decrypted_text
        
    except Exception as e:
        return False, f"שגיאה בפענוח: {str(e)}"

def decrypt_transcript_advanced(encrypted_data, password):
    """פענוח מתקדם - ניסיון עם מספר שיטות"""
    
    # שיטה 1: שימוש בפונקציה המקורית מ-secure_assemblyai
    try:
        from secure_assemblyai import decrypt_transcript_with_password
        decrypted_text = decrypt_transcript_with_password(encrypted_data, password)
        if decrypted_text:
            return True, decrypted_text
    except Exception as e1:
        print(f"שיטה 1 (secure_assemblyai) נכשלה: {str(e1)}")
    
    # שיטה 2: פענוח ישיר עם הסיסמה כמפתח
    try:
        # המרת הסיסמה למפתח Fernet תקין
        password_bytes = password.encode('utf-8')
        # הוספת padding אם נדרש
        while len(password_bytes) < 32:
            password_bytes += b'0'
        password_bytes = password_bytes[:32]  # חיתוך ל-32 בתים
        
        key = base64.urlsafe_b64encode(password_bytes)
        fernet = Fernet(key)
        
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        return True, decrypted_text
        
    except Exception as e2:
        print(f"שיטה 2 (ישיר) נכשלה: {str(e2)}")
    
    # שיטה 3: עם PBKDF2 וsalt ברירת מחדל
    try:
        key = derive_key_from_password(password)
        fernet = Fernet(key)
        
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        return True, decrypted_text
        
    except Exception as e3:
        print(f"שיטה 3 (PBKDF2) נכשלה: {str(e3)}")
    
    # שיטה 4: ניסיון עם salt שונה
    try:
        salt = b'secure_transcription_salt'
        key = derive_key_from_password(password, salt)
        fernet = Fernet(key)
        
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        return True, decrypted_text
        
    except Exception as e4:
        print(f"שיטה 4 (salt מיוחד) נכשלה: {str(e4)}")
    
    return False, "כל שיטות הפענוח נכשלו - בדוק שהסיסמה נכונה"

def main():
    """פונקציה ראשית"""
    if len(sys.argv) != 3:
        print("שימוש: python decrypt_transcript.py <נתיב_לקובץ> <סיסמה>")
        print("דוגמה: python decrypt_transcript.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json mypassword123")
        sys.exit(1)
    
    file_path = sys.argv[1]
    password = sys.argv[2]
    
    # בדיקה שהקובץ קיים
    if not os.path.exists(file_path):
        print(f"❌ הקובץ לא נמצא: {file_path}")
        sys.exit(1)
    
    try:
        # קריאת הקובץ
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # בדיקה שזה קובץ מוצפן
        if not data.get('is_encrypted', False):
            print("❌ הקובץ לא מוצפן")
            sys.exit(1)
        
        encrypted_transcript = data.get('encrypted_transcript')
        if not encrypted_transcript:
            print("❌ לא נמצא תמלול מוצפן בקובץ")
            sys.exit(1)
        
        print(f"🔐 מנסה לפענח קובץ: {file_path}")
        print(f"📝 מטופל: {data.get('patient_name', 'לא ידוע')}")
        print(f"📅 תאריך: {data.get('session_date', 'לא ידוע')}")
        print(f"🔒 שיטת הצפנה: {data.get('encryption_method', 'לא ידוע')}")
        print(f"📊 מילים: {data.get('word_count', 0)}")
        print()
        
        # ניסיון פענוח
        success, result = decrypt_transcript_advanced(encrypted_transcript, password)
        
        if success:
            print("✅ פענוח הצליח!")
            print("=" * 50)
            print("📄 התמלול המפוענח:")
            print("=" * 50)
            print(result)
            print("=" * 50)
            
            # שמירת התמלול המפוענח לקובץ
            output_file = file_path.replace('.json', '_decrypted.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"תמלול מפוענח - {data.get('patient_name', 'לא ידוע')}\n")
                f.write(f"תאריך: {data.get('session_date', 'לא ידוע')}\n")
                f.write(f"מילים: {data.get('word_count', 0)}\n")
                f.write("=" * 50 + "\n")
                f.write(result)
            
            print(f"💾 התמלול המפוענח נשמר גם בקובץ: {output_file}")
            
        else:
            print("❌ פענוח נכשל!")
            print(f"שגיאה: {result}")
            print()
            print("💡 טיפים:")
            print("- בדוק שהסיסמה נכונה")
            print("- ודא שזו הסיסמה שהשתמשת בה בעת יצירת התמלול")
            print("- הסיסמה רגישה לאותיות גדולות/קטנות")
            
    except Exception as e:
        print(f"❌ שגיאה בקריאת הקובץ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
