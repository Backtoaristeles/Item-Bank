import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from google.oauth2.service_account import Credentials
import math

# ---- CONFIGURATION ----
ORIGINAL_ITEM_CATEGORIES = {
    "Waystones": [
        "Waystone EXP + Delirious",
        "Waystone EXP 35%",
        "Waystone EXP"
    ],
    "Whites": [
        "Stellar Amulet",
        "Breach ring level 82",
        "Heavy Belt"
    ],
    "Tablets": [
        "Tablet Exp 9%+10% (random)",
        "Quantity Tablet (6%+)",
        "Grand Project Tablet"
    ],
    "Various": [
        "Logbook level 79-80"
    ]
}
ALL_ITEMS = sum(ORIGINAL_ITEM_CATEGORIES.values(), [])

CATEGORY_COLORS = {
    "Waystones": "#FFD700",   # Gold/Yellow
    "Whites": "#FFFFFF",      # White
    "Tablets": "#AA66CC",     # Purple
    "Various": "#42A5F5",     # Blue
}

SHEET_NAME = "poe_item_bank"
SHEET_TAB = "Sheet1"
TARGETS_TAB = "Targets"
INSTANT_TAB = "InstantSell"

# ---- GOOGLE SHEETS FUNCTIONS ----
def get_gsheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def load_data():
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet(SHEET_TAB)
    df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str)
    df = df.dropna(how='all')
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

def save_data(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet(SHEET_TAB)
    set_with_dataframe(sheet, df[["User", "Item", "Quantity"]], include_index=False)

def load_targets():
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet(TARGETS_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=TARGETS_TAB, rows=50, cols=3)
        ws.append_row(["Item", "Target", "Divines"])
    df = get_as_dataframe(ws, evaluate_formulas=True, dtype=str).dropna(how='all')
    targets = {}
    divines = {}
    if not df.empty and "Item" in df.columns:
        if "Target" not in df.columns:
            df["Target"] = 100
        if "Divines" not in df.columns:
            df["Divines"] = ""
        for idx, row in df.iterrows():
            item = row["Item"]
            try:
                targets[item] = int(float(row["Target"]))
            except Exception:
                targets[item] = 100
            try:
                divines[item] = float(row["Divines"]) if str(row["Divines"]).strip() != "" else 0
            except Exception:
                divines[item] = 0
    for item in ALL_ITEMS:
        if item not in targets:
            targets[item] = 100
        if item not in divines:
            divines[item] = 0
    return targets, divines, ws

def save_targets(targets, divines, ws):
    df = pd.DataFrame([{"Item": item, "Target": targets[item], "Divines": divines[item]} for item in ALL_ITEMS])
    ws.clear()
    set_with_dataframe(ws, df, include_index=False)

def load_instant_sell():
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet(INSTANT_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=INSTANT_TAB, rows=50, cols=2)
        ws.append_row(["Item", "InstantSellStack"])
    df = get_as_dataframe(ws, evaluate_formulas=True, dtype=str).dropna(how='all')
    instant_stacks = {}
    if not df.empty and "Item" in df.columns:
        for idx, row in df.iterrows():
            item = row["Item"]
            try:
                instant_stacks[item] = int(float(row["InstantSellStack"]))
            except Exception:
                instant_stacks[item] = 50
    for item in ALL_ITEMS:
        if item not in instant_stacks:
            instant_stacks[item] = 50
    return instant_stacks, ws

def save_instant_sell(instant_stacks, ws):
    df = pd.DataFrame([{"Item": item, "InstantSellStack": instant_stacks[item]} for item in ALL_ITEMS])
    ws.clear()
    set_with_dataframe(ws, df, include_index=False)

st.set_page_config(page_title="PoE Bulk Item Banking App", layout="wide")
st.title("PoE Bulk Item Banking App")

# ---- ADMIN LOGIN STATE HANDLING ----
if 'is_editor' not in st.session_state:
    st.session_state['is_editor'] = False
if 'show_login' not in st.session_state:
    st.session_state['show_login'] = False
if 'login_failed' not in st.session_state:
    st.session_state['login_failed'] = False

def logout():
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
            else:
                st.session_state['is_editor'] = False
                st.session_state['login_failed'] = True

# ---- TOP-CENTER ADMIN LOGIN BUTTON OR LOGOUT ----
col1, col2, col3 = st.columns([1,2,1])
with col2:
    if not st.session_state['is_editor']:
        if st.button("Admin login"):
            st.session_state['show_login'] = not st.session_state['show_login']
    else:
        if st.button("Admin logout"):
            logout()

if st.session_state['show_login'] and not st.session_state['is_editor']:
    col_spacer1, col_login, col_spacer2 = st.columns([1,2,1])
    with col_login:
        show_admin_login()
    if st.session_state['login_failed']:
        st.error("Incorrect username or password.")

if st.session_state['is_editor']:
    st.caption("**Admin mode enabled**")
else:
    st.caption("**Read only mode** (progress & deposit info only)")

# ---- DATA LOADING ----
df = load_data()
targets, divines, ws_targets = load_targets()
instant_stacks, ws_instant = load_instant_sell()

# ---- SETTINGS SIDEBAR ----
with st.sidebar:
    st.header("Per-Item Targets & Divine Value")
    if st.session_state['is_editor']:
        changed = False
        new_targets = {}
        new_divines = {}
        for item in ALL_ITEMS:
            cols = st.columns([2, 2])
            tgt =
