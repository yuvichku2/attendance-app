import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import pytz

# הגדרת אזור זמן ישראל
ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')

HEBREW_DAYS = {
    'Sunday': 'ראשון',
    'Monday': 'שני',
    'Tuesday': 'שלישי',
    'Wednesday': 'רביעי',
    'Thursday': 'חמישי',
    'Friday': 'שישי',
    'Saturday': 'שבת'
}

st.set_page_config(page_title="דיווח נוכחות עובדים", page_icon="⏰", layout="centered")

# --- חיבור ל-Google Sheets ---
@st.cache_resource
def get_spreadsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
    client = gspread.authorize(creds)
    return client.open("Employee_Attendance").worksheet("Logs")

try:
    sheet = get_spreadsheet()
except Exception as e:
    st.error(f"שגיאה בחיבור ל-Google Sheets: {e}")
    st.stop()

# --- ניהול משתמשים ---
USERS = {
    "yuval": {"name": "יובל", "pass": "1234", "role": "admin"},
    "sara": {"name": "שרה", "pass": "1234", "role": "admin"},
    "yoel": {"name": "יואל", "pass": "1234", "role": "admin"},
    "efrat": {"name": "אפרת", "pass": "1234", "role": "employee"},
    "tali": {"name": "טלי", "pass": "1234", "role": "employee"},
    "hai": {"name": "חי", "pass": "1234", "role": "employee"},
    "frida": {"name": "פרידה", "pass": "1234", "role": "employee"},
    "anat": {"name": "ענת", "pass": "1234", "role": "employee"}
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None

# --- מסך התחברות ---
if not st.session_state["logged_in"]:
    st.title("🔑 התחברות למערכת הנוכחות")
    username = st.text_input("שם משתמש").strip().lower()
    password = st.text_input("סיסמה", type="password")
    
    if st.button("התחבר", use_container_width=True, type="primary"):
        if username in USERS and USERS[username]["pass"] == password:
            st.session_state["logged_in"] = True
            st.session_state["user_info"] = USERS[username]
            st.rerun()
        else:
            st.error("שם משתמש או סיסמה שגויים")
    st.stop()

user = st.session_state["user_info"]

st.sidebar.write(f"שלום, **{user['name']}**")
if st.sidebar.button("התנתק"):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.rerun()

tabs = ["⏰ דיווח נוכחות"]
if user["role"] == "admin":
    tabs.append("📊 ריכוז שעות חודשי")

selected_tab = st.radio("ניווט", tabs, horizontal=True, label_visibility="collapsed")

# --- לשונית 1: דיווח נוכחות ---
if selected_tab == "⏰ דיווח נוכחות":
    st.title("⏰ דיווח נוכחות")
    
    now = datetime.now(ISRAEL_TZ)
    st.subheader(f"תאריך ושעה: {now.strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🟢 כניסה לעבודה", use_container_width=True, type="primary"):
            now = datetime.now(ISRAEL_TZ)
            row = [
                now.strftime("%Y-%m-%d"),
                user["name"],
                "כניסה",
                now.strftime("%H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S")
            ]
            sheet.append_row(row)
            st.success(f"נרשמה כניסה בהצלחה בשעה {now.strftime('%H:%M')}")

    with col2:
        if st.button("🔴 יציאה מעבודה", use_container_width=True):
            now = datetime.now(ISRAEL_TZ)
            row = [
                now.strftime("%Y-%m-%d"),
                user["name"],
                "יציאה",
                now.strftime("%H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S")
            ]
            sheet.append_row(row)
            st.warning(f"נרשמה יציאה בהצלחה בשעה {now.strftime('%H:%M')}")

    st.divider()

    st.write("### דיווחי היעדרות")
    col3, col4 = st.columns(2)

    with col3:
        if st.button("🏖️ יום חופשה", use_container_width=True):
            now = datetime.now(ISRAEL_TZ)
            row = [
                now.strftime("%Y-%m-%d"),
                user["name"],
                "חופשה",
                "-",
                now.strftime("%Y-%m-%d %H:%M:%S")
            ]
            sheet.append_row(row)
            st.info("נרשם יום חופשה בהצלחה")

    with col4:
        if st.button("🤒 יום מחלה", use_container_width=True):
            now = datetime.now(ISRAEL_TZ)
            row = [
                now.strftime("%Y-%m-%d"),
                user["name"],
                "מחלה",
                "-",
                now.strftime("%Y-%m-%d %H:%M:%S")
            ]
            sheet.append_row(row)
            st.info("נרשם יום מחלה בהצלחה")

# --- לשונית 2: ריכוז שעות חודשי ---
elif selected_tab == "📊 ריכוז שעות חודשי":
    st.title("📊 ריכוז שעות חודשי לעובדים")
    
    data = sheet.get_all_records()
    if not data:
        st.info("אין עדיין דיווחים בגיליון.")
    else:
        df = pd.DataFrame(data)
        
        if 'Timestamp' in df.columns and not df.empty:
            df['Date_dt'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date_dt'].dt.strftime('%Y-%m')
            
            col_m, col_e = st.columns(2)
            with col_m:
                available_months = sorted(df['Month'].unique(), reverse=True)
                selected_month = st.selectbox("בחר חודש:", available_months)
            with col_e:
                available_employees = sorted(df['Employee'].unique())
                selected_employee = st.selectbox("בחר עובד:", available_employees)
            
            # סינון לפי חודש ועובד
            emp_df = df[(df['Month'] == selected_month) & (df['Employee'] == selected_employee)].copy()
            
            if emp_df.empty:
                st.warning(f"אין נתונים עבור {selected_employee} בחודש {selected_month}")
            else:
                emp_df = emp_df.sort_values(by=['Date', 'Timestamp'])
                
                # עיבוד וריכוז ימי העבודה
                daily_records = []
                
                for date, group in emp_df.groupby('Date'):
                    day_obj = datetime.strptime(date, "%Y-%m-%d")
                    day_name = HEBREW_DAYS.get(day_obj.strftime("%A"), day_obj.strftime("%A"))
                    formatted_date = day_obj.strftime("%d/%m/%Y")
                    
                    types = group['Type'].tolist()
                    times = group['Time'].tolist()
                    
                    # טיפול בימי חופשה/מחלה
                    if "חופשה" in types:
                        daily_records.append({
                            "תאריך": formatted_date,
                            "יום בשבוע": day_name,
                            "שעת כניסה": "-",
                            "שעת יציאה": "-",
                            "סה\"כ שעות": "חופשה",
                            "hours_num": 0
                        })
                    elif "מחלה" in types:
                        daily_records.append({
                            "תאריך": formatted_date,
                            "יום בשבוע": day_name,
                            "שעת כניסה": "-",
                            "שעת יציאה": "-",
                            "סה\"כ שעות": "מחלה",
                            "hours_num": 0
                        })
                    else:
                        in_time = "-"
                        out_time = "-"
                        total_hours_str = "00:00"
                        hours_num = 0.0
                        
                        in_rows = group[group['Type'] == 'כניסה']
                        out_rows = group[group['Type'] == 'יציאה']
                        
                        if not in_rows.empty:
                            in_time = in_rows.iloc[0]['Time'][:5] # HH:MM
                        if not out_rows.empty:
                            out_time = out_rows.iloc[-1]['Time'][:5]
                            
                        if not in_rows.empty and not out_rows.empty:
                            t1 = datetime.strptime(in_rows.iloc[0]['Time'], "%H:%M:%S")
                            t2 = datetime.strptime(out_rows.iloc[-1]['Time'], "%H:%M:%S")
                            if t2 > t1:
                                diff = t2 - t1
                                total_seconds = int(diff.total_seconds())
                                hours = total_seconds // 3600
                                minutes = (total_seconds % 3600) // 60
                                total_hours_str = f"{hours:02d}:{minutes:02d}"
                                hours_num = round(total_seconds / 3600, 2)
                        
                        daily_records.append({
                            "תאריך": formatted_date,
                            "יום בשבוע": day_name,
                            "שעת כניסה": in_time,
                            "שעת יציאה": out_time,
                            "סה\"כ שעות": total_hours_str,
                            "hours_num": hours_num
                        })
                
                report_df = pd.DataFrame(daily_records)
                total_monthly_hours = sum(r['hours_num'] for r in daily_records)
                
                st.subheader(f"📋 דוח נוכחות עבור {selected_employee} - {selected_month}")
                st.dataframe(report_df[["תאריך", "יום בשבוע", "שעת כניסה", "שעת יציאה", "סה\"כ שעות"]], use_container_width=True)
                
                st.metric(label="סה\"כ שעות עבודה בחודש", value=f"{total_monthly_hours:.2f} שעות")
