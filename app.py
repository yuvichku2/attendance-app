import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import pytz

# הגדרת אזור זמן ישראל
ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')

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
    "israel": {"name": "ישראל ישראלי", "pass": "1234", "role": "employee"},
    "dana": {"name": "דנה לוי", "pass": "1234", "role": "employee"},
    "admin": {"name": "מנהל מערכת", "pass": "admin123", "role": "admin"}
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
    tabs.append("📊 דוח מנהל חודשי")

selected_tab = st.radio("ניווט", tabs, horizontal=True, label_visibility="collapsed")

# --- לשונית 1: דיווח נוכחות ---
if selected_tab == "⏰ דיווח נוכחות":
    st.title("⏰ דיווח נוכחות")
    
    now = datetime.now(ISRAEL_TZ)
    st.subheader(f"תאריך ושעה: {now.strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    # שורה 1: כניסה ויציאה
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

    # שורה 2: חופשה ומחלה
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

# --- לשונית 2: דוח מנהל חודשי ---
elif selected_tab == "📊 דוח מנהל חודשי":
    st.title("📊 דוח נוכחות מנהלי")
    
    data = sheet.get_all_records()
    if not data:
        st.info("אין עדיין דיווחים בגיליון.")
    else:
        df = pd.DataFrame(data)
        
        if 'Timestamp' in df.columns and not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df['Month'] = df['Timestamp'].dt.strftime('%Y-%m')
            
            available_months = sorted(df['Month'].unique(), reverse=True)
            selected_month = st.selectbox("בחר חודש לצפייה:", available_months)
            
            filtered_df = df[df['Month'] == selected_month]
            
            st.subheader(f"פירוט דיווחים לחודש {selected_month}")
            st.dataframe(filtered_df[['Date', 'Employee', 'Type', 'Time']], use_container_width=True)
