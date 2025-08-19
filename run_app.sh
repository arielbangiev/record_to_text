#!/bin/bash
# סקריפט להפעלת האפליקציה עם הסביבה הוירטואלית

echo "🚀 מפעיל את מערכת התמלול למטפלים..."
echo "📁 מיקום הפרויקט: $(pwd)"

# בדיקה אם קיימת סביבה וירטואלית
if [ ! -d "venv" ]; then
    echo "❌ לא נמצאה סביבה וירטואלית. יוצר סביבה חדשה..."
    python3 -m venv venv
    echo "✅ סביבה וירטואלית נוצרה"
fi

# הפעלת הסביבה הוירטואלית
echo "🔧 מפעיל סביבה וירטואלית..."
source venv/bin/activate

# בדיקה אם צריך להתקין חבילות
echo "📦 בודק חבילות נדרשות..."
if ! python -c "import flask" 2>/dev/null; then
    echo "📥 מתקין חבילות מ-requirements.txt..."
    pip install -r requirements.txt
    echo "✅ חבילות הותקנו בהצלחה"
else
    echo "✅ כל החבילות כבר מותקנות"
fi

# הפעלת האפליקציה
echo "🎯 מפעיל את האפליקציה..."
python app.py
