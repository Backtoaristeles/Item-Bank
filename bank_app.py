import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from google.oauth2.service_account import Credentials
from datetime import datetime
import math

# ---- CONFIGURATION ----
ORIGINAL_ITEM_CATEGORIES = {
    "Waystones": ["Waystone EXP + Delirious", "Waystone EXP 35%", "Waystone EXP"],
    "White Item Bases": ["Stellar Amulet", "Breach ring level 82", "Heavy Belt"],
    "Tablets": ["Tablet Exp 9%+10% (random)", "Quantity Tablet (6%+)", "Grand Project Tablet"],
    "Various": ["Logbook level 79-80"]
}
ALL_ITEMS = sum(ORIGINAL_ITEM_CATEGORIES.values(), [])
CATEGORY_COLORS = {"Waystones": "#FFD700", "White Item Bases": "#FFFFFF", "Tablets": "#AA66CC", "Various": "#42A5F5"}
ITEM_COLORS = {
    "Breach ring level 82": "#D6A4FF",
    "Stellar Amulet": "#FFD700",
    "Heavy Belt": "#A4FFA3",
    "Waystone EXP + Delirious": "#FF6961",
    "Waystone EXP 35%": "#FFB347",
    "Waystone EXP": "#FFB347",
    "Tablet Exp 9%+10% (random)": "#7FDBFF",
    "Quantity Tablet (6%+)": "#B0E0E6",
    "Grand Project Tablet": "#FFDCB9",
    "Logbook level 79-80": "#42A5F5"
}

def get_item_color(item):
    return ITEM_COLORS.get(item, "#FFF")

SHEET_NAME = "poe_item_bank"
SHEET_TAB = "Sheet1"
TARGETS_TAB = "Targets"
DEFAULT_BANK_BUY_PCT = 80

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

# ---- ADMIN LOGGING FUNCTION ----
def log_admin_action(action, details):
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet("AdminLogs")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="AdminLogs", rows=500, cols=3)
        ws.append_row(["Timestamp", "AdminAction", "Details"])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([timestamp, action, details])

def load_data():
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet(SHEET_TAB)
    df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str).dropna(how='all')
    if not df.empty:
        df = df.fillna("")
        expected_cols = ["User", "Item", "Quantity"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_cols]
    else:
        df = pd.DataFrame(columns=["User", "Item", "Quantity"])
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
    return df

def load_targets():
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet(TARGETS_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=TARGETS_TAB, rows=50, cols=4)
        ws.append_row(["Item", "Target", "Divines", "Link"])
    df = get_as_dataframe(ws, evaluate_formulas=True, dtype=str).dropna(how='all')
    targets, divines, links, bank_buy_pct = {}, {}, {}, DEFAULT_BANK_BUY_PCT
    if not df.empty and "Item" in df.columns:
        settings_row = df[df["Item"] == "_SETTINGS"]
        if not settings_row.empty:
            try:
                bank_buy_pct = int(float(settings_row.iloc[0]["Target"]))
            except Exception:
                bank_buy_pct = DEFAULT_BANK_BUY_PCT
        df = df[df["Item"] != "_SETTINGS"]
        if "Target" not in df.columns: df["Target"] = 100
        if "Divines" not in df.columns: df["Divines"] = ""
        if "Link" not in df.columns: df["Link"] = ""
        for idx, row in df.iterrows():
            item = row["Item"]
            targets[item] = int(float(row["Target"])) if str(row["Target"]).strip() != "" else 100
            divines[item] = float(row["Divines"]) if str(row["Divines"]).strip() != "" else 0
            links[item] = row["Link"]
    for item in ALL_ITEMS:
        targets.setdefault(item, 100)
        divines.setdefault(item, 0)
        links.setdefault(item, "")
    return targets, divines, links, bank_buy_pct, ws

def save_targets(targets, divines, links, bank_buy_pct, ws):
    data_rows = [{"Item": item, "Target": targets[item], "Divines": divines[item], "Link": links[item]} for item in ALL_ITEMS]
    data_rows.append({"Item": "_SETTINGS", "Target": bank_buy_pct, "Divines": "", "Link": ""})
    df = pd.DataFrame(data_rows)
    ws.clear()
    set_with_dataframe(ws, df, include_index=False)

def save_data(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet(SHEET_TAB)
    set_with_dataframe(sheet, df[["User", "Item", "Quantity"]], include_index=False)

st.set_page_config(page_title="PoE Bulk Item Banking App", layout="wide")
st.title("PoE Bulk Item Banking App")

if 'is_editor' not in st.session_state:
    st.session_state['is_editor'] = False
if 'show_login' not in st.session_state:
    st.session_state['show_login'] = False
if 'login_failed' not in st.session_state:
    st.session_state['login_failed'] = False

def logout():
    log_admin_action("Logout", "Admin logged out")
    st.session_state['is_editor'] = False
    st.session_state['show_login'] = False
    st.session_state['login_failed'] = False

def show_admin_login():
    with st.form("admin_login"):
        st.write("**Admin Login**")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            if username == "Admin" and password == "AdminPOEconomics":
                st.session_state['is_editor'] = True
                st.session_state['show_login'] = False
                st.session_state['login_failed'] = False
                log_admin_action("Login", "Admin logged in")
            else:
                st.session_state['is_editor'] = False
                st.session_state['login_failed'] = True

# ---- ADMIN LOGS DISPLAY ----
def load_admin_logs():
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet("AdminLogs")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="AdminLogs", rows=500, cols=3)
        ws.append_row(["Timestamp", "AdminAction", "Details"])
    df = get_as_dataframe(ws, evaluate_formulas=True, dtype=str).dropna(how='all')
    if not df.empty:
        df = df.fillna("")
    return df

if st.session_state['is_editor']:
    st.markdown("---")
    st.header("📜 Admin Logs")
    logs_df = load_admin_logs()
    if not logs_df.empty:
        st.dataframe(logs_df.tail(30), use_container_width=True)
    else:
        st.info("No admin logs yet.")
