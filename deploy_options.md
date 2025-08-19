# 🌐 אפשרויות הרצה מרוחקת לפרויקט

## 🚀 אפשרויות פריסה (Deployment)

### 1. GitHub Codespaces (מומלץ - חינמי!)
```bash
# פשוט לחץ על הכפתור הירוק "Code" ב-GitHub ובחר "Codespaces"
# זה יפתח את הפרויקט בענן עם VSCode מלא
```
**יתרונות:**
- חינמי (60 שעות חינם בחודש)
- סביבה מלאה עם VSCode
- אוטומטית מתקין את requirements.txt
- נגיש מכל מחשב עם דפדפן

### 2. Replit (קל מאוד)
1. לך ל-replit.com
2. לחץ "Import from GitHub"
3. הדבק: `https://github.com/arielbangiev/record_to_text`
4. Replit יזהה אוטומטית שזה פרויקט Python ויריץ אותו

### 3. Railway (מקצועי)
```bash
# התקן Railway CLI
npm install -g @railway/cli

# התחבר לחשבון
railway login

# פרוס את הפרויקט
railway deploy
```

### 4. Render (חינמי עד 750 שעות)
1. לך ל-render.com
2. חבר את GitHub
3. בחר את הפרויקט record_to_text
4. Render יפרוס אוטומטית

### 5. Heroku (קלאסי)
```bash
# התקן Heroku CLI
# צור Procfile
echo "web: python app.py" > Procfile

# פרוס
heroku create your-app-name
git push heroku main
```

### 6. Ngrok (לבדיקות מהירות)
```bash
# התקן ngrok
brew install ngrok  # macOS
# או הורד מ-ngrok.com

# הרץ את האפליקציה מקומית
./run_app.sh

# בטרמינל נוסף:
ngrok http 5000
```
זה ייתן לך URL זמני כמו: `https://abc123.ngrok.io`

## 🔧 הכנת הפרויקט לפריסה

### צור קובץ Procfile (לHeroku/Railway)
```
web: python app.py
```

### עדכן app.py לפריסה
```python
# בסוף app.py, שנה את:
if __name__ == '__main__':
    PORT = int(os.getenv('PORT', '5000'))
    app.run(debug=False, host='0.0.0.0', port=PORT)
```

### צור .env.example
```
ASSEMBLYAI_API_KEY=your-api-key-here
GOOGLE_CLIENT_ID=your-google-client-id
DEBUG=False
HOST=0.0.0.0
PORT=5000
```

## 🎯 המלצות לפי מטרה:

### לבדיקות מהירות:
- **Ngrok** - הכי מהיר, URL זמני

### לפיתוח:
- **GitHub Codespaces** - סביבה מלאה בענן

### לפרויקט אמיתי:
- **Railway** או **Render** - מקצועי וחינמי

### לפרוטוטיפ:
- **Replit** - הכי פשוט להתחיל

איזה אפשרות מעניינת אותך הכי הרבה?
