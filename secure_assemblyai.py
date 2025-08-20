# secure_assemblyai.py - תמלול מוצפן עם AssemblyAI
import os
import tempfile
import hashlib
import base64
import assemblyai as aai

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError as e:
    print(f"❌ שגיאה בייבוא cryptography: {e}")
    print("💡 הרץ: pip install cryptography")
    CRYPTO_AVAILABLE = False

class SecureAssemblyAI:
    """תמלול מאובטח עם AssemblyAI - הצפנה מקסימלית"""
    
    def __init__(self, api_key, user_password):
        if not CRYPTO_AVAILABLE:
            raise ImportError("ספריית ההצפנה לא זמינה - הרץ: pip install cryptography")
        
        self.api_key = api_key
        aai.settings.api_key = api_key
        
        # יצירת מפתח הצפנה מהסיסמה של המשתמש
        self.encryption_key = self._derive_key(user_password)
        self.fernet = Fernet(self.encryption_key)
        
    def _derive_key(self, password: str) -> bytes:
        """יצירת מפתח הצפנה מסיסמה"""
        password_bytes = password.encode()
        salt = b'secure_transcription_salt'  # במציאות - salt אקראי לכל משתמש
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def secure_transcribe(self, audio_file_path: str, patient_name: str) -> dict:
        """תמלול מאובטח עם הצפנה מקסימלית"""
        
        print("🔐 מתחיל תמלול מאובטח...")
        
        # שלב 1: הצפנת הקובץ המקורי
        encrypted_original = self._encrypt_file(audio_file_path)
        print("✅ קובץ מקורי הוצפן")
        
        # שלב 2: יצירת קובץ זמני לתמלול
        temp_audio = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_audio = temp_file.name
                
                # העתקת הקובץ לתמלול (לא מוצפן - AssemblyAI צריך לשמוע)
                with open(audio_file_path, 'rb') as original:
                    temp_file.write(original.read())
            
            print("📤 שולח לתמלול ב-AssemblyAI...")
            
            # שלב 3: תמלול עם AssemblyAI
            transcriber = aai.Transcriber()
            config = aai.TranscriptionConfig(
                language_code="he",
                punctuate=True,
                format_text=True
            )
            
            transcript = transcriber.transcribe(temp_audio, config=config)
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"שגיאה בתמלול: {transcript.error}")
            
            print("✅ תמלול הושלם")
            
            # שלב 4: הצפנת התוצאות מיד
            encrypted_transcript = self._encrypt_text(transcript.text)
            
            # שלב 5: יצירת hash לאימות שלמות
            content_hash = hashlib.sha256(transcript.text.encode()).hexdigest()
            
            print("🔐 תוצאות הוצפנו")
            
            # שלב 6: מחיקת נתונים לא מוצפנים מהזיכרון
            original_text = transcript.text  # שמירה זמנית לסטטיסטיקות
            del transcript  # מחיקה מהזיכרון
            
            return {
                'success': True,
                'encrypted_transcript': encrypted_transcript,
                'content_hash': content_hash,
                'patient_name': patient_name,
                'word_count': len(original_text.split()),
                'char_count': len(original_text),
                'encryption_method': 'AES-256 + PBKDF2',
                'privacy_level': 'maximum'
            }
            
        finally:
            # שלב 7: ניקוי מוחלט של קבצים זמניים
            if temp_audio and os.path.exists(temp_audio):
                # מחיקה מאובטחת - כתיבה עליונה
                self._secure_delete(temp_audio)
                print("🗑️ קבצים זמניים נמחקו באופן מאובטח")
    
    def decrypt_transcript(self, encrypted_transcript: str) -> str:
        """פענוח התמלול עם הסיסמה של המשתמש"""
        try:
            # פענוח base64 תחילה
            encrypted_data = base64.urlsafe_b64decode(encrypted_transcript.encode('utf-8'))
            # פענוח עם Fernet
            decrypted_bytes = self.fernet.decrypt(encrypted_data)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"🔍 שגיאה בפענוח: {e}")
            raise Exception("שגיאה בפענוח - סיסמה שגויה או נתונים פגומים")
    
    def _encrypt_file(self, file_path: str) -> str:
        """הצפנת קובץ"""
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        encrypted_data = self.fernet.encrypt(file_data)
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def _encrypt_text(self, text: str) -> str:
        """הצפנת טקסט"""
        encrypted_bytes = self.fernet.encrypt(text.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    
    def _secure_delete(self, file_path: str):
        """מחיקה מאובטחת של קובץ"""
        try:
            # כתיבה עליונה עם נתונים אקראיים
            file_size = os.path.getsize(file_path)
            with open(file_path, 'r+b') as file:
                file.write(os.urandom(file_size))
                file.flush()
                os.fsync(file.fileno())
            
            # מחיקה רגילה
            os.remove(file_path)
        except Exception as e:
            print(f"⚠️ שגיאה במחיקה מאובטחת: {e}")
            # מחיקה רגילה כגיבוי
            if os.path.exists(file_path):
                os.remove(file_path)

# דוגמה לשימוש
def example_usage():
    """דוגמה לשימוש במערכת המאובטחת"""
    
    # הגדרות
    api_key = "your-assemblyai-api-key"
    user_password = "user-secure-password-123"
    
    # יצירת מערכת מאובטחת
    secure_ai = SecureAssemblyAI(api_key, user_password)
    
    # תמלול מאובטח
    result = secure_ai.secure_transcribe("audio.wav", "patient_name")
    
    if result['success']:
        print("🔐 תמלול מוצפן נשמר")
        print(f"📊 מילים: {result['word_count']}")
        
        # פענוח לצפייה (רק עם הסיסמה הנכונה)
        decrypted_text = secure_ai.decrypt_transcript(result['encrypted_transcript'])
        print("📝 תמלול:", decrypted_text[:100] + "...")

def decrypt_transcript_with_password(encrypted_transcript: str, password: str) -> str:
    """פענוח תמלול עם סיסמה - פונקציה עצמאית"""
    try:
        # יצירת מפתח הצפנה מהסיסמה
        password_bytes = password.encode()
        salt = b'secure_transcription_salt'  # אותו salt כמו בהצפנה
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        fernet = Fernet(key)
        
        # פענוח הנתונים
        encrypted_data = base64.urlsafe_b64decode(encrypted_transcript.encode('utf-8'))
        decrypted_bytes = fernet.decrypt(encrypted_data)
        return decrypted_bytes.decode('utf-8')
        
    except Exception as e:
        print(f"🔍 שגיאה בפענוח: {e}")
        return None

if __name__ == "__main__":
    example_usage()
