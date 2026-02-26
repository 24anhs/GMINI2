import os
import re
from flask import Flask, request
import requests

app = Flask(__name__)

# --- הגדרות מערכת ---
YM_TOKEN = "WU1BUElL.apik_owJJz4IQ1z0pa_O-scE6rw.NTXls1kFwOLUwwYefyEXXFszW7y-qYl29gQVsVZU4d4"
TEMPLATE_ID = "1387640"
YM_API_URL = "https://www.call2all.co.il/ym/api/"

@app.route('/process_record', methods=['GET', 'POST'])
def process_record():
    # 1. שליפת נתיב הקובץ (מטפל גם בסימני ^ וגם ב- =)
    what = request.args.get('what')
    if not what:
        # בדיקה ידנית ב-URL למקרה שהפרמטרים הגיעו משובשים מהמערכת
        full_url = request.url
        match_what = re.search(r'what[\^=]([^&*]+)', full_url)
        if match_what:
            what = match_what.group(1)

    if not what:
        print(f"DEBUG: Could not find 'what' in URL: {request.url}")
        return "say_hebrew=שגיאה בזיהוי הקובץ&hangup=yes"

    # 2. ניקוי הנתיב ובניית כתובת לקובץ ה-TXT
    clean_path = what.replace('ivr2:', '').replace('ivr:', '')
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    
    txt_path = 'ivr' + clean_path.replace('.wav', '.txt')
    
    try:
        # 3. הורדת תוכן קובץ ה-TXT מימות המשיח
        file_res = requests.get(f"{YM_API_URL}DownloadFile", params={
            'token': YM_TOKEN, 
            'path': txt_path
        })
        raw_content = file_res.text.strip()
        print(f"DEBUG: Content from file: {raw_content}")

        # 4. חילוץ מספר הטלפון מתוך התבנית ConfBridge-...-Phone-052...
        match = re.search(r'Phone-(\d+)', raw_content)
        
        if not match:
            print("DEBUG: Phone pattern not found in text")
            return "say_hebrew=לא נמצא מספר טלפון תקין בקובץ המקליט&hangup=yes"
            
        phone_to_check = match.group(1)
        print(f"DEBUG: Extracted phone: {phone_to_check}")

        # 5. בדיקה ברשימת התפוצה
        check_res = requests.get(f"{YM_API_URL}GetTemplateList", params={
            'token': YM_TOKEN, 
            'templateId': TEMPLATE_ID, 
            'filter[phone]': phone_to_check
        }).json()
        
        is_exists = check_res.get('data') and len(check_res.get('data')) > 0
        
        # 6. הגדרת הפעולה
        if not is_exists:
            action, active_val, msg = 'add', '1', "המספר נוסף בהצלחה"
        else:
            action, active_val, msg = 'update', '0', "המספר עודכן כחסום"

        # 7. ביצוע העדכון בפועל
        update_res = requests.get(f"{YM_API_URL}UpdateTemplateList", params={
            'token': YM_TOKEN, 
            'templateId': TEMPLATE_ID, 
            'phone': phone_to_check, 
            'active': active_val, 
            'action': action
        }).json()
        print(f"DEBUG: Yemot update response: {update_res}")

        # 8. החזרת תשובה בפורמט תקני (שימוש ב- = וב- &)
        return f"say_hebrew={msg}&hangup=yes"

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return "say_hebrew=שגיאה בתקשורת הנתונים&hangup=yes"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
