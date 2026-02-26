import os
import re
from flask import Flask, request, Response

app = Flask(__name__)

# --- הגדרות מערכת ---
YM_TOKEN = "WU1BUElL.apik_owJJz4IQ1z0pa_O-scE6rw.NTXls1kFwOLUwwYefyEXXFszW7y-qYl29gQVsVZU4d4"
TEMPLATE_ID = "1387640"
YM_API_URL = "https://www.call2all.co.il/ym/api/"

@app.route('/process_record', methods=['GET', 'POST'])
def process_record():
    # 1. שליפת נתיב הקובץ
    full_url = request.url
    what = request.args.get('what')
    
    # ניסיון חילוץ אגרסיבי למקרה שהתווים משובשים ב-URL
    if not what:
        match_what = re.search(r'what[\^=]([^&*]+)', full_url)
        if match_what:
            what = match_what.group(1)

    if not what:
        return "say_hebrew=שגיאה בזיהוי הקובץ&hangup=yes"

    # 2. ניקוי נתיב לקובץ ה-TXT
    clean_path = what.replace('ivr2:', '').replace('ivr:', '')
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    txt_path = 'ivr' + clean_path.replace('.wav', '.txt')
    
    try:
        # 3. הורדת תוכן קובץ ה-TXT
        file_res = requests.get(f"{YM_API_URL}DownloadFile", params={
            'token': YM_TOKEN, 
            'path': txt_path
        })
        raw_content = file_res.text.strip()

        # 4. חילוץ מספר הטלפון (052...)
        match = re.search(r'Phone-(\d+)', raw_content)
        if not match:
            return "say_hebrew=מספר לא נמצא בקובץ&hangup=yes"
            
        phone_to_check = match.group(1)

        # 5. בדיקה ברשימת התפוצה
        check_res = requests.get(f"{YM_API_URL}GetTemplateList", params={
            'token': YM_TOKEN, 
            'templateId': TEMPLATE_ID, 
            'filter[phone]': phone_to_check
        }).json()
        
        is_exists = check_res.get('data') and len(check_res.get('data')) > 0
        
        # 6. הגדרת פעולה
        if not is_exists:
            action, active_val, msg = 'add', '1', "המספר נוסף בהצלחה"
        else:
            action, active_val, msg = 'update', '0', "המספר עודכן כחסום"

        # 7. ביצוע העדכון
        requests.get(f"{YM_API_URL}UpdateTemplateList", params={
            'token': YM_TOKEN, 
            'templateId': TEMPLATE_ID, 
            'phone': phone_to_check, 
            'active': active_val, 
            'action': action
        })

        # --- התיקון הקריטי כאן: החזרת טקסט נקי ללא המרות של השרת ---
        response_text = f"say_hebrew={msg}&hangup=yes"
        return Response(response_text, mimetype='text/plain')

    except Exception as e:
        return Response("say_hebrew=שגיאה בנתונים&hangup=yes", mimetype='text/plain')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
