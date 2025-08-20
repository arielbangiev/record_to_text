#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט פשוט לפענוח תמלולים מוצפנים באמצעות secure_assemblyai.py
"""

import sys
import json
import os

# ייבוא הפונקציות מהמערכת הקיימת
try:
    import sys
    import os
    # הוספת התיקייה הראשית לנתיב
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    from secure_assemblyai import decrypt_transcript_with_password
except ImportError:
    print("❌ לא ניתן לייבא את secure_assemblyai.py")
    print("ודא שהקובץ secure_assemblyai.py קיים בתיקייה הראשית")
    sys.exit(1)

def main():
    """פונקציה ראשית"""
    if len(sys.argv) < 2:
        print("🔐 סקריפט פענוח תמלולים מוצפנים")
        print("=" * 40)
        print("שימוש:")
        print("  python simple_decrypt.py <נתיב_לקובץ> [סיסמה]")
        print()
        print("דוגמאות:")
        print("  python simple_decrypt.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json")
        print("  python simple_decrypt.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json mypassword123")
        print()
        print("⚠️  שים לב לסדר: קובץ ואז סיסמה!")
        print("אם לא תספק סיסמה, תתבקש להזין אותה באופן אינטראקטיבי")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # בדיקה אם המשתמש הכניס את הסיסמה לפני הקובץ (טעות נפוצה)
    if not os.path.exists(file_path) and len(sys.argv) >= 3:
        # אולי המשתמש הכניס סיסמה ואז קובץ
        potential_file = sys.argv[2]
        if os.path.exists(potential_file):
            print("⚠️  נראה שהכנסת סיסמה לפני הקובץ!")
            print(f"💡 הסדר הנכון: python simple_decrypt.py '{potential_file}' '{file_path}'")
            print("🔄 מנסה לתקן אוטומטית...")
            file_path = potential_file
            # נעביר את הסיסמה לפרמטר הנכון
            if len(sys.argv) >= 3:
                sys.argv[2] = sys.argv[1]  # הסיסמה שהיתה במקום הראשון
    
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
        
        print(f"🔐 קובץ מוצפן נמצא: {file_path}")
        print(f"📝 מטופל: {data.get('patient_name', 'לא ידוע')}")
        print(f"📅 תאריך: {data.get('session_date', 'לא ידוע')}")
        print(f"🔒 שיטת הצפנה: {data.get('encryption_method', 'לא ידוע')}")
        print(f"📊 מילים: {data.get('word_count', 0)}")
        print()
        
        # קבלת סיסמה
        if len(sys.argv) >= 3:
            password = sys.argv[2]
        else:
            import getpass
            password = getpass.getpass("🔑 הזן סיסמת פענוח: ")
        
        if not password:
            print("❌ יש להזין סיסמה")
            sys.exit(1)
        
        print("🔄 מנסה לפענח...")
        
        # ניסיון פענוח באמצעות הפונקציה המקורית
        try:
            decrypted_text = decrypt_transcript_with_password(encrypted_transcript, password)
            
            if decrypted_text:
                print("✅ פענוח הצליח!")
                print("=" * 50)
                print("📄 התמלול המפוענח:")
                print("=" * 50)
                print(decrypted_text)
                print("=" * 50)
                
                # שמירת התמלול המפוענח לקובץ
                output_file = file_path.replace('.json', '_decrypted.txt')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"תמלול מפוענח - {data.get('patient_name', 'לא ידוע')}\n")
                    f.write(f"תאריך: {data.get('session_date', 'לא ידוע')}\n")
                    f.write(f"מילים: {data.get('word_count', 0)}\n")
                    f.write(f"שיטת הצפנה: {data.get('encryption_method', 'לא ידוע')}\n")
                    f.write("=" * 50 + "\n")
                    f.write(decrypted_text)
                
                print(f"💾 התמלול המפוענח נשמר גם בקובץ: {output_file}")
                
            else:
                print("❌ פענוח נכשל!")
                print("💡 טיפים:")
                print("- בדוק שהסיסמה נכונה")
                print("- ודא שזו הסיסמה שהשתמשת בה בעת יצירת התמלול")
                print("- הסיסמה רגישה לאותיות גדולות/קטנות")
                
        except Exception as e:
            print(f"❌ שגיאה בפענוח: {str(e)}")
            print("💡 נסה להשתמש ב-decrypt_transcript.py במקום")
            
    except Exception as e:
        print(f"❌ שגיאה בקריאת הקובץ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
