import os
from flask import Flask, request
import requests

app = Flask(__name__)

# --- הגדרות מערכת ---
YM_TOKEN = "WU1BUElL.apik_owJJz4IQ1z0pa_O-scE6rw.NTXls1kFwOLUwwYefyEXXFszW7y-qYl29gQVsVZU4d4"
TEMPLATE_ID = "1387640"
YM_API_URL = "https://www.call2all.co.il/ym/api/"

@app.route('/process_record', methods=['GET', 'POST'])
def process_record():
    # 1. קבלת נתיב הקובץ מהפרמטר 'what' (למשל ivr2:/3/000.wav)
    what = request.args.get('what', '')
    print(f"DEBUG: Received 'what' parameter: {what}")
    
    if not what:
        print("DEBUG: No 'what' parameter found.")
        return "say_hebrew=שגיאה, לא זוהה קובץ מתנגן&hangup"

    # 2. בניית נתיב לקובץ ה-TXT
    # מסירים ivr2: ומחליפים סיומת
    clean_path = what.replace('ivr2:', '')
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    
    # בימות המשיח, כשניגשים ב-API, הנתיב צריך להתחיל ב-ivr/
    txt_path = 'ivr' + clean_path.replace('.wav', '.txt')
    print(f"DEBUG: Calculated TXT path: {txt_path}")

    # 3. הורדת תוכן קובץ ה-TXT
    try:
        read_url = f"{YM_API_URL}DownloadFile"
        file_res = requests.get(read_url, params={'token': YM_TOKEN, 'path': txt_path})
        
        raw_content = file_res.text.strip()
        print(f"DEBUG: Raw content from file: '{raw_content}'")

        # חילוץ ספרות בלבד (מספר הטלפון)
        phone_to_check = "".join(filter(str.isdigit, raw_content))
        print(f"DEBUG: Extracted phone number: {phone_to_check}")

        if not phone_to_check or len(phone_to_check) < 7:
            print("DEBUG: Failed to extract a valid phone number.")
            return "say_hebrew=לא נמצא מספר טלפון תקין בקובץ המקליט&hangup"

        # 4. בדיקה ברשימת התפוצה
        check_url = f"{YM_API_URL}GetTemplateList"
        check_params = {
            'token': YM_TOKEN,
            'templateId': TEMPLATE_ID,
            'filter[phone]': phone_to_check
        }
        
        check_res = requests.get(check_url, params=check_params).json()
        print(f"DEBUG: GetTemplateList response: {check_res}")
        
        # בדיקה אם המספר קיים (בודקים ב-data)
        is_exists = check_res.get('data') and len(check_res.get('data')) > 0
        
        update_url = f"{YM_API_URL}UpdateTemplateList"
        
        if not is_exists:
            # הוספה כפעיל
            action_params = {
                'token': YM_TOKEN, 'templateId': TEMPLATE_ID,
                'phone': phone_to_check, 'active': '1', 'action': 'add'
            }
            msg = "המספר של המקליט נוסף לרשימה"
        else:
            # עדכון לחסום (active=0)
            action_params = {
                'token': YM_TOKEN, 'templateId': TEMPLATE_ID,
                'phone': phone_to_check, 'active': '0', 'action': 'update'
            }
            msg = "המספר של המקליט עודכן כחסום"

        final_res = requests.get(update_url, params=action_params).json()
        print(f"DEBUG: Update result: {final_res}")

        return f"say_hebrew={msg}&hangup"

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return "say_hebrew=ארעה שגיאה בחיבור למערכת הנתונים&hangup"

if __name__ == '__main__':
    # Render משתמש בפורט שמוגדר במשתני הסביבה
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
