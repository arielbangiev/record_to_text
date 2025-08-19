# treatment_form_generator.py - מחולל טופס טיפול מקצועי
import re
from datetime import datetime
from typing import Dict, List, Optional

class TreatmentFormGenerator:
    """מחולל טופס טיפול מקצועי מטקסט מתומלל"""
    
    def __init__(self):
        # מילות מפתח לזיהוי תחומים שונים בטיפול
        self.keywords = {
            'presenting_problem': [
                'בעיה', 'קושי', 'מתקשה', 'סובל', 'כואב', 'מרגיש', 'חרדה', 'דיכאון',
                'לחץ', 'מתח', 'פחד', 'דאגה', 'בעיות', 'קשיים', 'מצב רוח', 'רגשות'
            ],
            'symptoms': [
                'תסמין', 'תסמינים', 'כאב', 'עייפות', 'נדודי שינה', 'בעיות שינה',
                'אובדן תיאבון', 'עצבנות', 'רגזנות', 'בכי', 'התקפי חרדה'
            ],
            'background': [
                'היסטוריה', 'עבר', 'ילדות', 'משפחה', 'הורים', 'אח', 'אחות',
                'נישואין', 'גירושין', 'עבודה', 'לימודים', 'צבא'
            ],
            'current_situation': [
                'כרגע', 'עכשיו', 'היום', 'השבוע', 'החודש', 'לאחרונה',
                'בזמן האחרון', 'בתקופה האחרונה'
            ],
            'goals': [
                'מטרה', 'מטרות', 'רוצה', 'מעוניין', 'מקווה', 'חלום', 'שאיפה',
                'לשפר', 'לפתור', 'להתמודד', 'ללמוד'
            ],
            'resources': [
                'תמיכה', 'עזרה', 'חברים', 'משפחה', 'כוחות', 'יכולות',
                'הצלחות', 'הישגים', 'חוזקות'
            ],
            'interventions': [
                'טיפול', 'התערבות', 'תרגיל', 'משימה', 'המלצה', 'עצה',
                'אסטרטגיה', 'טכניקה', 'כלי'
            ]
        }
        
        # תבניות משפטים נפוצות
        self.sentence_patterns = {
            'feeling_expressions': r'(אני מרגיש|מרגישה|חש|חשה|מרגיש שאני|מרגישה שאני)',
            'problem_statements': r'(הבעיה שלי|הקושי שלי|מה שמטריד אותי|מה שקשה לי)',
            'time_references': r'(לפני|אחרי|במשך|כבר|עדיין|תמיד|לעולם|לפעמים)',
            'intensity_words': r'(מאוד|הרבה|קצת|מעט|לגמרי|בכלל|ממש|די)'
        }

    def generate_treatment_form(self, transcript_text: str, patient_name: str, 
                              session_date: str, therapist_name: str = "") -> Dict:
        """יצירת טופס טיפול מקצועי מטקסט מתומלל"""
        
        # ניתוח הטקסט
        analysis = self._analyze_transcript(transcript_text)
        
        # יצירת הטופס
        treatment_form = {
            'header': {
                'patient_name': patient_name,
                'session_date': session_date,
                'therapist_name': therapist_name,
                'session_number': 1,  # ניתן לעדכן בהתאם
                'form_created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            'presenting_problem': {
                'main_concerns': analysis.get('presenting_problem', []),
                'duration': analysis.get('problem_duration', 'לא צוין'),
                'severity': analysis.get('severity_level', 'בינונית'),
                'impact_on_functioning': analysis.get('functioning_impact', [])
            },
            'symptoms_assessment': {
                'reported_symptoms': analysis.get('symptoms', []),
                'symptom_frequency': analysis.get('symptom_frequency', {}),
                'triggers': analysis.get('triggers', []),
                'coping_mechanisms': analysis.get('coping', [])
            },
            'background_information': {
                'relevant_history': analysis.get('background', []),
                'family_dynamics': analysis.get('family_info', []),
                'social_support': analysis.get('support_system', []),
                'previous_treatment': analysis.get('previous_treatment', [])
            },
            'current_functioning': {
                'work_academic': analysis.get('work_functioning', []),
                'relationships': analysis.get('relationship_functioning', []),
                'daily_activities': analysis.get('daily_functioning', []),
                'self_care': analysis.get('self_care', [])
            },
            'treatment_goals': {
                'short_term_goals': analysis.get('short_term_goals', []),
                'long_term_goals': analysis.get('long_term_goals', []),
                'patient_priorities': analysis.get('patient_priorities', [])
            },
            'clinical_observations': {
                'mood_affect': analysis.get('mood_observations', []),
                'thought_process': analysis.get('thought_observations', []),
                'behavior_observations': analysis.get('behavior_observations', []),
                'insight_motivation': analysis.get('insight_level', 'בינונית')
            },
            'treatment_plan': {
                'recommended_interventions': analysis.get('interventions', []),
                'homework_assignments': analysis.get('homework', []),
                'next_session_focus': analysis.get('next_session', []),
                'frequency_duration': 'שבועי, 50 דקות'  # ברירת מחדל
            },
            'risk_assessment': {
                'suicide_risk': analysis.get('suicide_risk', 'נמוך'),
                'self_harm_risk': analysis.get('self_harm_risk', 'נמוך'),
                'safety_plan': analysis.get('safety_plan', [])
            },
            'additional_notes': {
                'therapist_observations': analysis.get('therapist_notes', []),
                'cultural_considerations': analysis.get('cultural_factors', []),
                'medication_notes': analysis.get('medication_info', [])
            },
            'raw_transcript': transcript_text,
            'analysis_confidence': analysis.get('confidence_score', 0.7)
        }
        
        return treatment_form

    def _analyze_transcript(self, text: str) -> Dict:
        """ניתוח מעמיק של הטקסט המתומלל"""
        
        sentences = self._split_into_sentences(text)
        analysis = {}
        
        # ניתוח לפי קטגוריות
        analysis['presenting_problem'] = self._extract_presenting_problems(sentences)
        analysis['symptoms'] = self._extract_symptoms(sentences)
        analysis['background'] = self._extract_background_info(sentences)
        analysis['goals'] = self._extract_goals(sentences)
        analysis['mood_observations'] = self._analyze_mood_indicators(sentences)
        analysis['functioning_impact'] = self._analyze_functioning(sentences)
        analysis['coping'] = self._extract_coping_mechanisms(sentences)
        analysis['support_system'] = self._extract_support_system(sentences)
        analysis['severity_level'] = self._assess_severity(sentences)
        analysis['confidence_score'] = self._calculate_confidence(sentences)
        
        return analysis

    def _split_into_sentences(self, text: str) -> List[str]:
        """חלוקת הטקסט למשפטים"""
        # ניקוי ראשוני
        text = re.sub(r'\s+', ' ', text.strip())
        
        # חלוקה למשפטים לפי סימני פיסוק
        sentences = re.split(r'[.!?]+', text)
        
        # ניקוי משפטים ריקים וקצרים מדי
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        
        return sentences

    def _extract_presenting_problems(self, sentences: List[str]) -> List[str]:
        """זיהוי הבעיות המרכזיות שהמטופל מציג"""
        problems = []
        
        for sentence in sentences:
            # חיפוש מילות מפתח של בעיות
            for keyword in self.keywords['presenting_problem']:
                if keyword in sentence:
                    # ניסיון לחלץ את ההקשר המלא
                    problem_context = self._extract_context(sentence, keyword)
                    if problem_context and problem_context not in problems:
                        problems.append(problem_context)
                    break
        
        return problems[:5]  # מגביל ל-5 בעיות מרכזיות

    def _extract_symptoms(self, sentences: List[str]) -> List[str]:
        """זיהוי תסמינים שהמטופל מדווח עליהם"""
        symptoms = []
        
        for sentence in sentences:
            for keyword in self.keywords['symptoms']:
                if keyword in sentence:
                    symptom_context = self._extract_context(sentence, keyword)
                    if symptom_context and symptom_context not in symptoms:
                        symptoms.append(symptom_context)
                    break
        
        return symptoms

    def _extract_background_info(self, sentences: List[str]) -> List[str]:
        """חילוץ מידע רקע רלוונטי"""
        background = []
        
        for sentence in sentences:
            for keyword in self.keywords['background']:
                if keyword in sentence:
                    bg_context = self._extract_context(sentence, keyword)
                    if bg_context and bg_context not in background:
                        background.append(bg_context)
                    break
        
        return background

    def _extract_goals(self, sentences: List[str]) -> List[str]:
        """זיהוי מטרות טיפוליות מהטקסט"""
        goals = []
        
        for sentence in sentences:
            for keyword in self.keywords['goals']:
                if keyword in sentence:
                    goal_context = self._extract_context(sentence, keyword)
                    if goal_context and goal_context not in goals:
                        goals.append(goal_context)
                    break
        
        return goals

    def _analyze_mood_indicators(self, sentences: List[str]) -> List[str]:
        """ניתוח אינדיקטורים של מצב רוח ורגשות"""
        mood_indicators = []
        
        emotion_words = [
            'עצוב', 'שמח', 'כועס', 'חרד', 'מודאג', 'מתוח', 'רגוע',
            'מתוסכל', 'מאוכזב', 'מבולבל', 'בטוח', 'לא בטוח'
        ]
        
        for sentence in sentences:
            for emotion in emotion_words:
                if emotion in sentence:
                    mood_context = self._extract_context(sentence, emotion)
                    if mood_context and mood_context not in mood_indicators:
                        mood_indicators.append(mood_context)
                    break
        
        return mood_indicators

    def _analyze_functioning(self, sentences: List[str]) -> List[str]:
        """ניתוח השפעה על תפקוד יומיומי"""
        functioning = []
        
        functioning_areas = [
            'עבודה', 'לימודים', 'משפחה', 'חברים', 'שינה', 'אכילה',
            'ספורט', 'תחביבים', 'יציאות', 'בית'
        ]
        
        for sentence in sentences:
            for area in functioning_areas:
                if area in sentence:
                    func_context = self._extract_context(sentence, area)
                    if func_context and func_context not in functioning:
                        functioning.append(func_context)
                    break
        
        return functioning

    def _extract_coping_mechanisms(self, sentences: List[str]) -> List[str]:
        """זיהוי אסטרטגיות התמודדות"""
        coping = []
        
        coping_words = [
            'מתמודד', 'עוזר', 'עוזרת', 'מרגיע', 'מרגיעה', 'פותר',
            'מנסה', 'עושה', 'הולך', 'הולכת', 'מדבר', 'מדברת'
        ]
        
        for sentence in sentences:
            for word in coping_words:
                if word in sentence:
                    coping_context = self._extract_context(sentence, word)
                    if coping_context and coping_context not in coping:
                        coping.append(coping_context)
                    break
        
        return coping

    def _extract_support_system(self, sentences: List[str]) -> List[str]:
        """זיהוי מערכת תמיכה"""
        support = []
        
        support_words = [
            'תמיכה', 'עזרה', 'חברים', 'משפחה', 'בן זוג', 'בת זוג',
            'הורים', 'ילדים', 'אחים', 'קרובים'
        ]
        
        for sentence in sentences:
            for word in support_words:
                if word in sentence:
                    support_context = self._extract_context(sentence, word)
                    if support_context and support_context not in support:
                        support.append(support_context)
                    break
        
        return support

    def _assess_severity(self, sentences: List[str]) -> str:
        """הערכת חומרת המצב"""
        severity_indicators = {
            'high': ['לא יכול', 'לא מצליח', 'נורא', 'איום', 'בלתי נסבל', 'הרס'],
            'medium': ['קשה', 'מתקשה', 'בעיה', 'קושי', 'לא קל'],
            'low': ['קצת', 'מעט', 'לפעמים', 'בסדר', 'יכול']
        }
        
        high_count = sum(1 for sentence in sentences 
                        for word in severity_indicators['high'] 
                        if word in sentence)
        
        medium_count = sum(1 for sentence in sentences 
                          for word in severity_indicators['medium'] 
                          if word in sentence)
        
        low_count = sum(1 for sentence in sentences 
                       for word in severity_indicators['low'] 
                       if word in sentence)
        
        if high_count > medium_count and high_count > low_count:
            return 'גבוהה'
        elif medium_count > low_count:
            return 'בינונית'
        else:
            return 'נמוכה'

    def _extract_context(self, sentence: str, keyword: str) -> str:
        """חילוץ הקשר מלא סביב מילת מפתח"""
        # מחזיר את המשפט המלא אם הוא לא ארוך מדי
        if len(sentence) <= 100:
            return sentence.strip()
        
        # אם המשפט ארוך, מנסה לחלץ חלק רלוונטי
        words = sentence.split()
        keyword_index = -1
        
        for i, word in enumerate(words):
            if keyword in word:
                keyword_index = i
                break
        
        if keyword_index != -1:
            start = max(0, keyword_index - 5)
            end = min(len(words), keyword_index + 6)
            context = ' '.join(words[start:end])
            return context.strip()
        
        return sentence.strip()

    def _calculate_confidence(self, sentences: List[str]) -> float:
        """חישוב רמת ביטחון בניתוח"""
        total_sentences = len(sentences)
        if total_sentences == 0:
            return 0.0
        
        # ספירת משפטים עם מילות מפתח רלוונטיות
        relevant_sentences = 0
        all_keywords = []
        for category in self.keywords.values():
            all_keywords.extend(category)
        
        for sentence in sentences:
            for keyword in all_keywords:
                if keyword in sentence:
                    relevant_sentences += 1
                    break
        
        confidence = relevant_sentences / total_sentences
        return min(confidence, 1.0)

    def format_treatment_form_html(self, treatment_form: Dict) -> str:
        """עיצוב הטופס לתצוגה ב-HTML"""
        
        html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>טופס טיפול - {treatment_form['header']['patient_name']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 20px;
            background: #f8f9fa;
            color: #2c3e50;
        }}
        .treatment-form {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            max-width: 900px;
            margin: 0 auto;
        }}
        .form-header {{
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .form-header h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 2.2em;
        }}
        .patient-info {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .patient-info p {{
            margin: 5px 0;
            font-weight: bold;
        }}
        .form-section {{
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }}
        .form-section h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 15px;
            font-size: 1.4em;
        }}
        .section-content ul {{
            padding-right: 20px;
        }}
        .section-content li {{
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        .section-content p {{
            margin-bottom: 10px;
        }}
        .actions {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: #ecf0f1;
            border-radius: 8px;
        }}
        .print-btn, .download-btn {{
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
            color: white;
        }}
        .print-btn {{
            background: #3498db;
        }}
        .print-btn:hover {{
            background: #2980b9;
        }}
        .download-btn {{
            background: #27ae60;
        }}
        .download-btn:hover {{
            background: #229954;
        }}
        @media print {{
            .actions {{ display: none; }}
            body {{ margin: 0; background: white; }}
            .treatment-form {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="actions">
        <button class="print-btn" onclick="window.print()">🖨️ הדפס טופס</button>
        <button class="download-btn" onclick="downloadTextForm()">💾 הורד כקובץ טקסט</button>
    </div>
    
    <div class="treatment-form">
        <div class="form-header">
            <h2>🏥 טופס טיפול מקצועי</h2>
            <div class="patient-info">
                <p><strong>שם המטופל:</strong> {treatment_form['header']['patient_name']}</p>
                <p><strong>תאריך הסשן:</strong> {treatment_form['header']['session_date']}</p>
                <p><strong>מטפל:</strong> {treatment_form['header']['therapist_name']}</p>
                <p><strong>נוצר:</strong> {treatment_form['header']['form_created']}</p>
            </div>
        </div>
        
        <div class="form-section">
            <h3>🎯 הבעיה המרכזית</h3>
            <div class="section-content">
                <p><strong>דאגות עיקריות:</strong></p>
                <ul>
                    {''.join(f'<li>{concern}</li>' for concern in treatment_form['presenting_problem']['main_concerns'])}
                </ul>
                <p><strong>חומרת המצב:</strong> {treatment_form['presenting_problem']['severity']}</p>
            </div>
        </div>
        
        <div class="form-section">
            <h3>🩺 הערכת תסמינים</h3>
            <div class="section-content">
                <p><strong>תסמינים מדווחים:</strong></p>
                <ul>
                    {''.join(f'<li>{symptom}</li>' for symptom in treatment_form['symptoms_assessment']['reported_symptoms'])}
                </ul>
                <p><strong>אסטרטגיות התמודדות:</strong></p>
                <ul>
                    {''.join(f'<li>{coping}</li>' for coping in treatment_form['symptoms_assessment']['coping_mechanisms'])}
                </ul>
            </div>
        </div>
        
        <div class="form-section">
            <h3>📋 מידע רקע</h3>
            <div class="section-content">
                <ul>
                    {''.join(f'<li>{bg}</li>' for bg in treatment_form['background_information']['relevant_history'])}
                </ul>
            </div>
        </div>
        
        <div class="form-section">
            <h3>🎯 מטרות טיפוליות</h3>
            <div class="section-content">
                <ul>
                    {''.join(f'<li>{goal}</li>' for goal in treatment_form['treatment_goals']['short_term_goals'])}
                </ul>
            </div>
        </div>
        
        <div class="form-section">
            <h3>👁️ תצפיות קליניות</h3>
            <div class="section-content">
                <p><strong>מצב רוח ורגשות:</strong></p>
                <ul>
                    {''.join(f'<li>{mood}</li>' for mood in treatment_form['clinical_observations']['mood_affect'])}
                </ul>
            </div>
        </div>
        
        <div class="form-section">
            <h3>📈 תוכנית טיפול</h3>
            <div class="section-content">
                <p><strong>התערבויות מומלצות:</strong></p>
                <ul>
                    {''.join(f'<li>{intervention}</li>' for intervention in treatment_form['treatment_plan']['recommended_interventions'])}
                </ul>
                <p><strong>תדירות מפגשים:</strong> {treatment_form['treatment_plan']['frequency_duration']}</p>
            </div>
        </div>
        
        <div class="form-section">
            <h3>⚠️ הערכת סיכונים</h3>
            <div class="section-content">
                <p><strong>סיכון אובדני:</strong> {treatment_form['risk_assessment']['suicide_risk']}</p>
                <p><strong>סיכון פגיעה עצמית:</strong> {treatment_form['risk_assessment']['self_harm_risk']}</p>
            </div>
        </div>
        
        <div class="form-section">
            <h3>📊 מידע נוסף</h3>
            <div class="section-content">
                <p><strong>רמת ביטחון בניתוח:</strong> {treatment_form['analysis_confidence']:.1%}</p>
                <p><em>הטופס נוצר אוטומטית מתמלול הסשן ודורש בדיקה מקצועית</em></p>
            </div>
        </div>
    </div>
    
    <script>
        function downloadTextForm() {{
            const textContent = `{treatment_form['raw_transcript'].replace('`', '\\`')}`;
            const blob = new Blob([textContent], {{ type: 'text/plain;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'treatment_form_{treatment_form['header']['patient_name']}_{treatment_form['header']['session_date']}.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>"""
        
        return html

    def export_to_word_format(self, treatment_form: Dict) -> str:
        """יצוא הטופס לפורמט טקסט מובנה לWord"""
        
        content = f"""
טופס טיפול מקצועי
==================

פרטי המטופל והסשן:
שם המטופל: {treatment_form['header']['patient_name']}
תאריך הסשן: {treatment_form['header']['session_date']}
מטפל: {treatment_form['header']['therapist_name']}
מספר סשן: {treatment_form['header']['session_number']}
תאריך יצירת הטופס: {treatment_form['header']['form_created']}

הבעיה המרכזית:
===============
דאגות עיקריות:
{chr(10).join(f'• {concern}' for concern in treatment_form['presenting_problem']['main_concerns'])}

חומרת המצב: {treatment_form['presenting_problem']['severity']}
משך הבעיה: {treatment_form['presenting_problem']['duration']}

השפעה על תפקוד:
{chr(10).join(f'• {impact}' for impact in treatment_form['presenting_problem']['impact_on_functioning'])}

הערכת תסמינים:
===============
תסמינים מדווחים:
{chr(10).join(f'• {symptom}' for symptom in treatment_form['symptoms_assessment']['reported_symptoms'])}

גורמים מעוררים:
{chr(10).join(f'• {trigger}' for trigger in treatment_form['symptoms_assessment']['triggers'])}

אסטרטגיות התמודדות:
{chr(10).join(f'• {coping}' for coping in treatment_form['symptoms_assessment']['coping_mechanisms'])}

מידע רקע:
==========
היסטוריה רלוונטית:
{chr(10).join(f'• {bg}' for bg in treatment_form['background_information']['relevant_history'])}

דינמיקה משפחתית:
{chr(10).join(f'• {family}' for family in treatment_form['background_information']['family_dynamics'])}

תמיכה חברתית:
{chr(10).join(f'• {support}' for support in treatment_form['background_information']['social_support'])}

תפקוד נוכחי:
=============
עבודה/לימודים:
{chr(10).join(f'• {work}' for work in treatment_form['current_functioning']['work_academic'])}

יחסים בינאישיים:
{chr(10).join(f'• {rel}' for rel in treatment_form['current_functioning']['relationships'])}

פעילויות יומיומיות:
{chr(10).join(f'• {daily}' for daily in treatment_form['current_functioning']['daily_activities'])}

מטרות טיפוליות:
===============
מטרות קצרות טווח:
{chr(10).join(f'• {goal}' for goal in treatment_form['treatment_goals']['short_term_goals'])}

מטרות ארוכות טווח:
{chr(10).join(f'• {goal}' for goal in treatment_form['treatment_goals']['long_term_goals'])}

עדיפויות המטופל:
{chr(10).join(f'• {priority}' for priority in treatment_form['treatment_goals']['patient_priorities'])}

תצפיות קליניות:
===============
מצב רוח ורגשות:
{chr(10).join(f'• {mood}' for mood in treatment_form['clinical_observations']['mood_affect'])}

תהליכי חשיבה:
{chr(10).join(f'• {thought}' for thought in treatment_form['clinical_observations']['thought_process'])}

התנהגות:
{chr(10).join(f'• {behavior}' for behavior in treatment_form['clinical_observations']['behavior_observations'])}

רמת תובנה ומוטיבציה: {treatment_form['clinical_observations']['insight_motivation']}

תוכנית טיפול:
=============
התערבויות מומלצות:
{chr(10).join(f'• {intervention}' for intervention in treatment_form['treatment_plan']['recommended_interventions'])}

משימות בית:
{chr(10).join(f'• {hw}' for hw in treatment_form['treatment_plan']['homework_assignments'])}

מיקוד הסשן הבא:
{chr(10).join(f'• {focus}' for focus in treatment_form['treatment_plan']['next_session_focus'])}

תדירות ומשך הטיפול: {treatment_form['treatment_plan']['frequency_duration']}

הערכת סיכונים:
===============
סיכון אובדני: {treatment_form['risk_assessment']['suicide_risk']}
סיכון פגיעה עצמית: {treatment_form['risk_assessment']['self_harm_risk']}

תוכנית בטיחות:
{chr(10).join(f'• {safety}' for safety in treatment_form['risk_assessment']['safety_plan'])}

הערות נוספות:
==============
תצפיות המטפל:
{chr(10).join(f'• {note}' for note in treatment_form['additional_notes']['therapist_observations'])}

שיקולים תרבותיים:
{chr(10).join(f'• {cultural}' for cultural in treatment_form['additional_notes']['cultural_considerations'])}

הערות תרופתיות:
{chr(10).join(f'• {med}' for med in treatment_form['additional_notes']['medication_notes'])}

רמת ביטחון בניתוח: {treatment_form['analysis_confidence']:.1%}

הערה: טופס זה נוצר אוטומטית מתמלול הסשן ודורש בדיקה וערכה מקצועית.

תמלול מקורי:
=============
{treatment_form['raw_transcript']}
"""
        
        return content
