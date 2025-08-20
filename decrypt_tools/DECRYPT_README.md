# 🔐 מדריך פענוח תמלולים מוצפנים

## סקירה כללית

המערכת שלנו יוצרת תמלולים מוצפנים עם הצפנה מקסימלית (AES-256 + PBKDF2). כדי לפענח תמלולים מוצפנים, יש לך מספר אפשרויות:

## 📁 קבצים מוצפנים

קבצי התמלולים המוצפנים נמצאים בתיקייה:
```
transcripts/user_X/[שם_מטופל]/secure_session_[תאריך].json
```

כל קובץ מכיל:
- `encrypted_transcript` - התמלול המוצפן
- `encryption_method` - שיטת ההצפנה (AES-256 + PBKDF2)
- `privacy_level` - רמת הפרטיות (maximum)
- `word_count` - מספר מילים
- `is_encrypted: true` - סימון שהקובץ מוצפן

## 🛠️ כלי פענוח

### 1. simple_decrypt.py (מומלץ)
הכלי הפשוט ביותר - משתמש בקוד המקורי של המערכת:

```bash
# עם סיסמה בשורת הפקודה
python decrypt_tools/simple_decrypt.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json mypassword123

# הזנת סיסמה אינטראקטיבית (מאובטח יותר)
python decrypt_tools/simple_decrypt.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json
```

### 2. decrypt_transcript.py (מתקדם)
כלי מתקדם עם מספר שיטות פענוח:

```bash
python decrypt_tools/decrypt_transcript.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json mypassword123
```

### 3. דרך האפליקציה
1. היכנס לאפליקציה: `http://localhost:5000/app`
2. בחר "🔐 AssemblyAI מאובטח" בתפריט שירות התמלול
3. הזן את הסיסמה במודל היפה החדש
4. הסשנים המוצפנים יופיעו ברשימת המטופלים

## 🔑 חשוב לזכור

### סיסמת ההצפנה
- **רק אתה יודע את הסיסמה** - המערכת לא שומרת אותה
- הסיסמה רגישה לאותיות גדולות/קטנות
- נדרשים לפחות 8 תווים
- בלי הסיסמה הנכונה, לא ניתן לפענח את התמלול

### אבטחה מקסימלית
- התמלול מוצפן עם AES-256 (הצפנה צבאית)
- השימוש ב-PBKDF2 מקשה על פיצוח
- גם אם מישהו יגיש לקובץ, הוא לא יוכל לקרוא אותו בלי הסיסמה

## 📋 דוגמאות שימוש

### דוגמה 1: פענוח בסיסי
```bash
python decrypt_tools/simple_decrypt.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json
# תתבקש להזין סיסמה: ********
```

### דוגמה 2: פענוח עם שמירה לקובץ
```bash
python decrypt_tools/decrypt_transcript.py transcripts/user_1/חיים/secure_session_2025-08-20_17-24-53.json mypassword123
# יווצר קובץ: secure_session_2025-08-20_17-24-53_decrypted.txt
```

### דוגמה 3: פענוח כל הקבצים בתיקייה
```bash
# Linux/Mac
for file in transcripts/user_1/*/secure_session_*.json; do
    python decrypt_tools/simple_decrypt.py "$file" mypassword123
done

# Windows PowerShell
Get-ChildItem -Path "transcripts\user_1\*\secure_session_*.json" | ForEach-Object {
    python decrypt_tools/simple_decrypt.py $_.FullName mypassword123
}
```

## ⚠️ פתרון בעיות

### "פענוח נכשל"
1. **בדוק את הסיסמה** - ודא שזו הסיסמה הנכונה
2. **רגישות לאותיות** - בדוק אותיות גדולות/קטנות
3. **תווים מיוחדים** - ודא שהסיסמה הוקלדה נכון
4. **נסה כלי אחר** - אם `simple_decrypt.py` לא עובד, נסה `decrypt_transcript.py`

### "קובץ לא נמצא"
1. בדוק את הנתיב לקובץ
2. ודא שהקובץ קיים בתיקייה
3. השתמש בנתיב מלא אם נדרש

### "שגיאת ייבוא"
1. ודא שאתה בתיקייה הנכונה
2. בדוק ש-`secure_assemblyai.py` קיים
3. התקן את החבילות הנדרשות: `pip install cryptography`

## 🔧 התקנת תלויות

אם אתה מקבל שגיאות, התקן את החבילות הנדרשות:

```bash
pip install cryptography
```

או:

```bash
pip install -r requirements.txt
```

## 💡 טיפים

1. **שמור את הסיסמה במקום בטוח** - בלעדיה התמלולים לא נגישים
2. **השתמש בסיסמאות חזקות** - לפחות 12 תווים עם מספרים ותווים מיוחדים
3. **גבה את הקבצים המוצפנים** - הם מכילים את כל המידע החשוב
4. **בדוק תמיד שהפענוח עבד** - לפני מחיקת הקובץ המקורי

## 🆘 עזרה נוספת

אם אתה נתקל בבעיות:
1. בדוק את הלוגים בטרמינל
2. ודא שהקובץ אכן מוצפן (`"is_encrypted": true`)
3. נסה עם קובץ אחר כדי לוודא שהבעיה לא בסיסמה
4. פנה לתמיכה טכנית אם הבעיה נמשכת

---

**זכור: הצפנה מקסימלית = אבטחה מקסימלית, אבל גם אחריות מקסימלית לשמירת הסיסמה! 🔐**
