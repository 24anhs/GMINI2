import os
import re
from flask import Flask, request
import requests

app = Flask(__name__)

# --- הגדרות - שנה אותן לפרטים שלך ---
YM_TOKEN = "YOUR_YM_TOKEN"  # הטוקן שלך מימות המשיח
TEMPLATE_ID = "1"           # מזהה רשימת התפוצה שלך

YM_API_URL = "https://www.call2all.co.il/ym/api/"

def get_phone_from_filename(filename):
    """
    מחלץ את מספר הטלפון משם הקובץ.
    קבצי הקלטה בימות נראים בדרך כלל כך: M1234-0501234567.wav
    """
    match = re.search(r'-(\d+)\.', filename)
    if match:
        return match.group(1)
    return None

@app.route('/process_record', methods=['GET', 'POST'])
def process_record():
    # 1. קבלת נתונים מימות המשיח
    # ימות המשיח שולחים את שם הקובץ המתנגן בפרמטר ApiFile
    current_file = request.args.get('ApiFile', '')
    
    if not current_file:
        return "say_hebrew=שגיאה, לא נמצא קובץ מתנגן&hangup"

    phone_to_check = get_phone_from_filename(current_file)
    
    if not phone_to_check:
        return "say_hebrew=שגיאה בחילוץ מספר הטלפון&hangup"

    # 2. בדיקה האם המספר קיים ברשימה
    check_url = f"{YM_API_URL}GetTemplateList"
    check_params = {
        'token': YM_TOKEN,
        'templateId': TEMPLATE_ID,
        'filter[phone]': phone_to_check
    }
    
    response = requests.get(check_url, params=check_params).json()
    
    # 3. לוגיקת הוספה / חסימה
    update_url = f"{YM_API_URL}UpdateTemplateList"
    
    # אם ברשימת הנתונים שחזרה יש איברים, סימן שהמספר קיים
    is_exists = len(response.get('data', [])) > 0

    if not is_exists:
        # מקרה א': לא קיים -> הוספה כפעיל
        action_params = {
            'token': YM_TOKEN,
            'templateId': TEMPLATE_ID,
            'phone': phone_to_check,
            'active': '1', # 1 = פעיל
            'action': 'add'
        }
        msg = "המספר נוסף בהצלחה לרשימה"
    else:
        # מקרה ב': קיים -> עדכון לחסום
        action_params = {
            'token': YM_TOKEN,
            'templateId': TEMPLATE_ID,
            'phone': phone_to_check,
            'active': '0', # 0 = חסום/לא פעיל
            'action': 'update'
        }
        msg = "המספר היה קיים וכעת עודכן כחסום"

    # ביצוע הפעולה מול ימות המשיח
    requests.get(update_url, params=action_params)

    # החזרת תשובה קולית למחייג
    return f"say_hebrew={msg}&go_to_folder=."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
