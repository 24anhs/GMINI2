import os
import re
from flask import Flask, request
import requests

app = Flask(__name__)

# --- הגדרות מערכת ---
# הטוקן ומזהה הרשימה כפי שסיפקת
YM_TOKEN = "WU1BUElL.apik_owJJz4IQ1z0pa_O-scE6rw.NTXls1kFwOLUwwYefyEXXFszW7y-qYl29gQVsVZU4d4"
TEMPLATE_ID = "1387640"
YM_API_URL = "https://www.call2all.co.il/ym/api/"

@app.route('/process_record', methods=['GET', 'POST'])
def process_record():
    # 1. קבלת נתיב הקובץ
    what = request.args.get('what', '')
    if not what:
        return "say_hebrew=שגיאה בפרמטרים&hangup=yes"

    # 2. ניקוי נתיב ובניית כתובת לקובץ ה-TXT
    # הסרת קידומות ימות המשיח כדי לקבל נתיב נקי
    clean_path = what.replace('ivr2:', '').replace('ivr:', '')
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    
    # הוספת ivr/ בתחילת הנתיב לצורך הורדה ב-API
    txt_path = 'ivr' + clean_path.replace('.wav', '.txt')
    
    try:
        # 3. הורדת תוכן קובץ ה-TXT
        file_res = requests.get(f"{YM_API_URL}DownloadFile", params={
            'token': YM_TOKEN, 
            'path': txt_path
        })
        raw_content = file_res.text.strip()
        
        # 4. חילוץ מספר הטלפון בעזרת Regex (מחפש את מה שאחרי Phone-)
        match = re.search(r'Phone-(\d+)', raw_content)
        
        if not match:
            return "say_hebrew=לא נמצא מספר טלפון תקין בקובץ&hangup=yes"
            
        phone_to_check = match.group(1)

        # 5. בדיקה האם קיים ברשימת התפוצה
        check_res = requests.get(f"{YM_API_URL}GetTemplateList", params={
            'token': YM_TOKEN, 
            'templateId': TEMPLATE_ID, 
            'filter[phone]': phone_to_check
        }).json()
        
        # זיהוי אם המספר קיים
        is_exists = check_res.get('data') and len(check_res.get('data')) > 0
        
        # 6. הגדרת פעולה: הוספה כחדש (1) או עדכון לחסום (0)
        if not is_exists:
            action, active_val, msg = 'add', '1', "המספר נוסף בהצלחה"
        else:
            action, active_val, msg = 'update', '0', "המספר עודכן כחסום"

        # ביצוע העדכון בפועל בימות המשיח
        requests.get(f"{YM_API_URL}UpdateTemplateList", params={
            'token': YM_TOKEN, 
            'templateId': TEMPLATE_ID, 
            'phone': phone_to_check, 
            'active': active_val, 
            'action': action
        })

        # החזרת פקודה קולית בפורמט שימות המשיח מבינים (עם = ו-&)
        return f"say_hebrew={msg}&hangup=yes"

    except Exception as e:
        print(f"Error: {str(e)}")
        return "say_hebrew=שגיאה בתקשורת הנתונים&hangup=yes"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
