import io
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import pytz
import streamlit as st

# הגדרת אזור זמן ישראל
ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')

HEBREW_DAYS = {
    'Sunday': 'ראשון',
    'Monday': 'שני',
    'Tuesday': 'שלישי',
    'Wednesday': 'רביעי',
    'Thursday': 'חמישי',
    'Friday': 'שישי',
    'Saturday': 'שבת',
}

st.set_page_config(
    page_title="דיווח נוכחות עובדים", page_icon="⏰", layout="centered"
)


# --- חיבור ל-Google Sheets ---
@st.cache_resource
def get_spreadsheet():
  scopes = [
      'https://www.googleapis.com/auth/spreadsheets',
      'https://www.googleapis.com/auth/drive',
  ]
  if 'gcp_service_account' in st.secrets:
    creds = Credentials.from_service_account_info(
        st.secrets['gcp_service_account'], scopes=scopes
    )
  else:
    creds = Credentials.from_service_account_file(
        'credentials.json', scopes=scopes
    )

  client = gspread.authorize(creds)
  return client.open('Employee_Attendance').worksheet('Logs')


try:
  sheet = get_spreadsheet()
except Exception as e:
  st.error(f'שגיאה בחיבור ל-Google Sheets: {e}')
  st.stop()

# --- ניהול משתמשים ---
USERS = {
    'yuval': {'name': 'יובל', 'pass': '1234', 'role': 'admin'},
    'sara': {'name': 'שרה', 'pass': '1234', 'role': 'admin'},
    'yoel': {'name': 'יואל', 'pass': '1234', 'role': 'admin'},
    'atar': {'name': 'עתר', 'pass': '1234', 'role': 'employee'},
    'efrat': {'name': 'אפרת', 'pass': '1234', 'role': 'employee'},
    'tali': {'name': 'טלי', 'pass': '1234', 'role': 'employee'},
    'hai': {'name': 'חי', 'pass': '1234', 'role': 'employee'},
    'frida': {'name': 'פרידה', 'pass': '1234', 'role': 'employee'},
    'anat': {'name': 'ענת', 'pass': '1234', 'role': 'employee'},
}

if 'logged_in' not in st.session_state:
  st.session_state['logged_in'] = False
  st.session_state['user_info'] = None

# --- מסך התחברות ---
if not st.session_state['logged_in']:
  st.title('🔑 התחברות למערכת הנוכחות')
  username = st.text_input('שם משתמש').strip().lower()
  password = st.text_input('סיסמה', type='password')

  if st.button('התחבר', use_container_width=True, type='primary'):
    if username in USERS and USERS[username]['pass'] == password:
      st.session_state['logged_in'] = True
      st.session_state['user_info'] = USERS[username]
      st.rerun()
    else:
      st.error('שם משתמש או סיסמה שגויים')
  st.stop()

user = st.session_state['user_info']

st.sidebar.write(f"שלום, **{user['name']}**")
if st.sidebar.button('התנתק'):
  st.session_state['logged_in'] = False
  st.session_state['user_info'] = None
  st.rerun()

tabs = ['⏰ דיווח נוכחות']
if user['role'] == 'admin':
  tabs.append('📊 ריכוז שעות חודשי')

selected_tab = st.radio(
    'ניווט', tabs, horizontal=True, label_visibility='collapsed'
)


# פונקציה משופרת לחישור זוגות כניסה/יציאה מרובים
def process_employee_days(emp_df):
  emp_df = emp_df.sort_values(by=['Date', 'Timestamp'])
  daily_records = []

  for date, group in emp_df.groupby('Date'):
    day_obj = datetime.strptime(date, '%Y-%m-%d')
    day_name = HEBREW_DAYS.get(day_obj.strftime('%A'), day_obj.strftime('%A'))
    formatted_date = day_obj.strftime('%d/%m/%Y')

    types = group['Type'].tolist()

    if 'חופשה' in types:
      daily_records.append({
          'תאריך': formatted_date,
          'יום בשבוע': day_name,
          'שעת כניסה': '-',
          'שעת יציאה': '-',
          'סה"כ שעות': 'חופשה',
          'hours_num': 0.0,
      })
    elif 'מחלה' in types:
      daily_records.append({
          'תאריך': formatted_date,
          'יום בשבוע': day_name,
          'שעת כניסה': '-',
          'שעת יציאה': '-',
          'סה"כ שעות': 'מחלה',
          'hours_num': 0.0,
      })
    else:
      in_times = []
      out_times = []
      total_seconds = 0
      last_in_time = None

      # סריקה כרונולוגית של הדיווחים באותו יום
      for _, row in group.iterrows():
        action_type = row['Type']
        time_str = row['Time']

        if action_type == 'כניסה':
          in_times.append(time_str[:5])
          if last_in_time is None:
            last_in_time = datetime.strptime(time_str, '%H:%M:%S')
        elif action_type == 'יציאה':
          out_times.append(time_str[:5])
          if last_in_time is not None:
            out_dt = datetime.strptime(time_str, '%H:%M:%S')
            if out_dt > last_in_time:
              total_seconds += int((out_dt - last_in_time).total_seconds())
            last_in_time = None

      # פירמוט תצוגה
      in_display = ', '.join(in_times) if in_times else '-'
      out_display = ', '.join(out_times) if out_times else '-'

      hours = total_seconds // 3600
      minutes = (total_seconds % 3600) // 60
      total_hours_str = f'{hours:02d}:{minutes:02d}'
      hours_num = round(total_seconds / 3600, 2)

      daily_records.append({
          'תאריך': formatted_date,
          'יום בשבוע': day_name,
          'שעת כניסה': in_display,
          'שעת יציאה': out_display,
          'סה"כ שעות': total_hours_str,
          'hours_num': hours_num,
      })
  return daily_records


# --- לשונית 1: דיווח נוכחות ---
if selected_tab == '⏰ דיווח נוכחות':
  st.title('⏰ דיווח נוכחות')

  now = datetime.now(ISRAEL_TZ)
  st.subheader(f"תאריך ושעה: {now.strftime('%d/%m/%Y %H:%M')}")
  st.divider()

  col1, col2 = st.columns(2)

  with col1:
    if st.button('🟢 כניסה לעבודה', use_container_width=True, type='primary'):
      now = datetime.now(ISRAEL_TZ)
      row = [
          now.strftime('%Y-%m-%d'),
          user['name'],
          'כניסה',
          now.strftime('%H:%M:%S'),
          now.strftime('%Y-%m-%d %H:%M:%S'),
      ]
      sheet.append_row(row)
      st.success(f"נרשמה כניסה בהצלחה בשעה {now.strftime('%H:%M')}")

  with col2:
    if st.button('🔴 יציאה מעבודה', use_container_width=True):
      now = datetime.now(ISRAEL_TZ)
      row = [
          now.strftime('%Y-%m-%d'),
          user['name'],
          'יציאה',
          now.strftime('%H:%M:%S'),
          now.strftime('%Y-%m-%d %H:%M:%S'),
      ]
      sheet.append_row(row)
      st.warning(f"נרשמה יציאה בהצלחה בשעה {now.strftime('%H:%M')}")

  st.divider()

  st.write('### דיווחי היעדרות')
  col3, col4 = st.columns(2)

  with col3:
    if st.button('🏖️ יום חופשה', use_container_width=True):
      now = datetime.now(ISRAEL_TZ)
      row = [
          now.strftime('%Y-%m-%d'),
          user['name'],
          'חופשה',
          '-',
          now.strftime('%Y-%m-%d %H:%M:%S'),
      ]
      sheet.append_row(row)
      st.info('נרשם יום חופשה בהצלחה')

  with col4:
    if st.button('🤒 יום מחלה', use_container_width=True):
      now = datetime.now(ISRAEL_TZ)
      row = [
          now.strftime('%Y-%m-%d'),
          user['name'],
          'מחלה',
          '-',
          now.strftime('%Y-%m-%d %H:%M:%S'),
      ]
      sheet.append_row(row)
      st.info('נרשם יום מחלה בהצלחה')

# --- לשונית 2: ריכוז שעות חודשי מנהלי ---
elif selected_tab == '📊 ריכוז שעות חודשי':
  st.title('📊 ריכוז שעות חודשי מופרד לפי עובד')

  # קריאת נתונים עדכנית בכל טעינה
  data = sheet.get_all_records()
  if not data:
    st.info('אין עדיין דיווחים בגיליון.')
  else:
    df = pd.DataFrame(data)

    if 'Timestamp' in df.columns and not df.empty:
      df['Date_dt'] = pd.to_datetime(df['Date'])
      df['Month'] = df['Date_dt'].dt.strftime('%Y-%m')

      available_months = sorted(df['Month'].unique(), reverse=True)
      selected_month = st.selectbox('בחר חודש לצפייה:', available_months)

      month_df = df[df['Month'] == selected_month].copy()
      employees = sorted(month_df['Employee'].unique())

      if not employees:
        st.warning(f'אין דיווחים בחודש {selected_month}')
      else:
        # יצירת קובץ Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
          summary_rows = []
          for emp in employees:
            emp_records = process_employee_days(
                month_df[month_df['Employee'] == emp]
            )
            emp_rep_df = pd.DataFrame(emp_records)
            tot_h = sum(r['hours_num'] for r in emp_records)

            summary_rows.append(
                {'שם עובד': emp, "סה'כ שעות": round(tot_h, 2)}
            )

            export_df = emp_rep_df[
                ['תאריך', 'יום בשבוע', 'שעת כניסה', 'שעת יציאה', 'סה"כ שעות']
            ]
            export_df.to_excel(writer, sheet_name=emp, index=False)

          pd.DataFrame(summary_rows).to_excel(
              writer, sheet_name='ריכוז כללי', index=False
          )

        st.download_button(
            label=f'📥 הורד דוח Excel חודשי ({selected_month}) - עמוד לכל עובד',
            data=excel_buffer.getvalue(),
            file_name=f'attendance_report_{selected_month}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type='primary',
        )

        st.divider()

        # תצוגת לשוניות לפי עובדים
        st.subheader('צפייה לפי עובד:')
        emp_tabs = st.tabs(employees)

        for i, emp in enumerate(employees):
          with emp_tabs[i]:
            emp_records = process_employee_days(
                month_df[month_df['Employee'] == emp]
            )
            emp_rep_df = pd.DataFrame(emp_records)
            tot_h = sum(r['hours_num'] for r in emp_records)

            st.dataframe(
                emp_rep_df[[
                    'תאריך',
                    'יום בשבוע',
                    'שעת כניסה',
                    'שעת יציאה',
                    'סה"כ שעות',
                ]],
                use_container_width=True,
            )

            st.metric(
                label=f"סה\"כ שעות עבודה בחודש עבור {emp}",
                value=f'{tot_h:.2f} שעות',
            )
