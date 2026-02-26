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
    what = request.args.get('what', '')
    if not what:
        return "say_hebrew=שגיאה, לא זוהה קובץ מתנגן&hangup"

    # בניית נתיב לקובץ ה-TXT
    clean_path = what.replace('ivr2:', '')
    if not clean_path.startswith('/'): clean_path = '/' + clean_path
    txt_path = 'ivr' + clean_path.replace('.wav', '.txt')

    try:
        # הורדת תוכן קובץ ה-TXT
        file_res = requests.get(f"{YM_API_URL}DownloadFile", params={'token': YM_TOKEN, 'path': txt_path})
        raw_content = file_res.text.strip()
        print(f"DEBUG: Raw content: {raw_content}")

        # חילוץ המספר שמופיע אחרי "Phone-" ולפני המקף הבא
        # Regex שמחפש את התבנית הספציפית ששלחת
        match = re.search(r'Phone-(\d+)', raw_content)
        
        if match:
            phone_to_check = match.group(1)
            print(f"DEBUG: Successfully extracted phone: {phone_to_check}")
        else:
            print("DEBUG: Could not find Phone pattern in text")
            return "say_hebrew=לא נמצא מספר טלפון בפורמט התקין&hangup"

        # בדיקה ברשימת התפוצה
        check_res = requests.get(f"{YM_API_URL}GetTemplateList", params={
            'token': YM_TOKEN, 'templateId': TEMPLATE_ID, 'filter[phone]': phone_to_check
        }).json()
        
        # זיהוי אם קיים (לפי הלוג שלך התשובה חוזרת במבנה מסוים)
        is_exists = check_res.get('data') and len(check_res.get('data')) > 0
        
        if not is_exists:
            action, active_val, msg = 'add', '1', "המספר נוסף בהצלחה"
        else:
            action, active_val, msg = 'update', '0', "המספר עודכן כחסום"

        # ביצוע העדכון
        requests.get(f"{YM_API_URL}UpdateTemplateList", params={
            'token': YM_TOKEN, 'templateId': TEMPLATE_ID, 
            'phone': phone_to_check, 'active': active_val, 'action': action
        })

        return f"say_hebrew={msg}&hangup"

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return "say_hebrew=שגיאה בחיבור לנתונים&hangup"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
