import os
from flask import Flask, request
import requests

app = Flask(__name__)

# הגדרות (מומלץ להגדיר ב-Environment של Render)
YM_TOKEN = os.environ.get('YM_TOKEN', 'YOUR_TOKEN_HERE')
YM_API_URL = "https://www.call2all.co.il/ym/api/"
TEMPLATE_ID = os.environ.get('TEMPLATE_ID', '1')

@app.route('/process_record', methods=['GET', 'POST'])
def process_record():
    # 1. קבלת נתיב הקובץ שמתנגן כרגע (למשל ivr2:/3/000.wav)
    what = request.args.get('what', '')
    
    if not what:
        return "say_hebrew=לא זוהה קובץ מתנגן&hangup"

    # 2. הפיכת הנתיב לנתיב של קובץ ה-txt (החלפת .wav ב-.txt)
    # אנחנו צריכים להסיר את הקידומת ivr2: אם היא קיימת
    clean_path = what.replace('ivr2:', '')
    txt_path = clean_path.replace('.wav', '.txt')
    
    print(f"DEBUG: Trying to read phone from: {txt_path}")

    # 3. קריאת תוכן קובץ ה-txt מימות המשיח
    read_url = f"{YM_API_URL}DownloadFile"
    read_params = {
        'token': YM_TOKEN,
        'path': txt_path
    }
    
    try:
        file_res = requests.get(read_url, params=read_params)
        phone_to_check = file_res.text.strip() # המספר שנמצא בתוך הקובץ
        
        # ניקוי תווים לא רצויים אם יש
        phone_to_check = "".join(filter(str.isdigit, phone_to_check))

        print(f"DEBUG: Phone extracted from TXT: {phone_to_check}")

        if not phone_to_check or len(phone_to_check) < 7:
            return "say_hebrew=לא נמצא מספר טלפון תקין בקובץ הטקסט&hangup"

        # 4. בדיקה ועדכון ברשימת התפוצה (כמו קודם)
        check_url = f"{YM_API_URL}GetTemplateList"
        check_params = {
            'token': YM_TOKEN,
            'templateId': TEMPLATE_ID,
            'filter[phone]': phone_to_check
        }
        
        response = requests.get(check_url, params=check_params).json()
        
        # בימות המשיח התשובה נמצאת ב-data או fullData תלוי בגרסה
        is_exists = response.get('data') and len(response.get('data')) > 0
        
        update_url = f"{YM_API_URL}UpdateTemplateList"
        
        if not is_exists:
            action_params = {
                'token': YM_TOKEN, 'templateId': TEMPLATE_ID,
                'phone': phone_to_check, 'active': '1', 'action': 'add'
            }
            msg = "המספר של המקליט נוסף לרשימה"
        else:
            action_params = {
                'token': YM_TOKEN, 'templateId': TEMPLATE_ID,
                'phone': phone_to_check, 'active': '0', 'action': 'update'
            }
            msg = "המספר של המקליט עודכן כחסום"

        requests.get(update_url, params=action_params)
        return f"say_hebrew={msg}&hangup"

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return "say_hebrew=שגיאה בתהליך חילוץ הנתונים&hangup"

if __name__ == '__main__':
    app.run()
