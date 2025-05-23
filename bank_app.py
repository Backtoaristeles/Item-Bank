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
        ws = sh.add_worksheet(title=INSTANT_TAB, rows=50, cols=3)
        ws.append_row(["Item", "StackSize", "SellPrice"])
    df = get_as_dataframe(ws, evaluate_formulas=True, dtype=str).dropna(how='all')
    stack_sizes = {}
    sell_prices = {}
    if not df.empty and "Item" in df.columns:
        if "StackSize" not in df.columns:
            df["StackSize"] = 50
        if "SellPrice" not in df.columns:
            df["SellPrice"] = ""
        for idx, row in df.iterrows():
            item = row["Item"]
            try:
                stack_sizes[item] = int(float(row["StackSize"]))
            except Exception:
                stack_sizes[item] = 50
            try:
                sell_prices[item] = float(row["SellPrice"]) if str(row["SellPrice"]).strip() != "" else 0
            except Exception:
                sell_prices[item] = 0
    for item in ALL_ITEMS:
        if item not in stack_sizes:
            stack_sizes[item] = 50
        if item not in sell_prices:
            sell_prices[item] = 0
    return stack_sizes, sell_prices, ws

def save_instant_sell(stack_sizes, sell_prices, ws):
    df = pd.DataFrame([{"Item": item, "StackSize": stack_sizes[item], "SellPrice": sell_prices[item]} for item in ALL_ITEMS])
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
stack_sizes, sell_prices, ws_instant = load_instant_sell()

# ---- SETTINGS SIDEBAR ----
with st.sidebar:
    st.header("Per-Item Targets & Divine Value")
    if st.session_state['is_editor']:
        changed = False
        changed_instant = False
        new_targets = {}
        new_divines = {}
        new_stack_sizes = {}
        new_sell_prices = {}
        st.subheader("Sell/Instant Sell Settings")
        for item in ALL_ITEMS:
            cols = st.columns([2, 2, 2, 2])
            tgt = cols[0].number_input(
                f"{item} target",
                min_value=1,
                value=targets.get(item, 100),
                step=1,
                key=f"target_{item}"
            )
            div = cols[1].number_input(
                f"Stack Value (Divines)",
                min_value=0.0,
                value=float(divines.get(item, 0)),
                step=0.1,
                format="%.2f",
                key=f"divine_{item}"
            )
            stack = cols[2].number_input(
                f"Instant Sell Stack",
                min_value=1,
                value=stack_sizes.get(item, 50),
                step=1,
                key=f"instant_stack_{item}"
            )
            sell = cols[3].number_input(
                f"Sell Price (Divines, per stack)",
                min_value=0.0,
                value=sell_prices.get(item, 0),
                step=0.1,
                format="%.2f",
                key=f"instant_price_{item}"
            )
            if tgt != targets[item] or div != divines[item]:
                changed = True
            if stack != stack_sizes[item] or sell != sell_prices[item]:
                changed_instant = True
            new_targets[item] = tgt
            new_divines[item] = div
            new_stack_sizes[item] = stack
            new_sell_prices[item] = sell
        if st.button("Save Targets & Values") and changed:
            save_targets(new_targets, new_divines, ws_targets)
            st.success("Targets and Divine values saved! Refresh the page to see updated progress bars and values.")
            st.stop()
        if st.button("Save Instant Sell Settings") and changed_instant:
            save_instant_sell(new_stack_sizes, new_sell_prices, ws_instant)
            st.success("Instant sell settings saved! Refresh the page to see updated instant sell prices.")
            st.stop()
    else:
        for item in ALL_ITEMS:
            st.text(f"{item}: Target = {targets[item]}, Stack Value = {divines[item]:.2f} Divines")

# --- MULTI-ITEM DEPOSIT FORM (EDITORS ONLY) ---
if st.session_state['is_editor']:
    with st.form("multi_item_deposit", clear_on_submit=True):
        st.subheader("Add a Deposit (multiple items per user)")
        user = st.text_input("User")
        col1, col2 = st.columns(2)
        item_qtys = {}
        for i, item in enumerate(ALL_ITEMS):
            col = col1 if i % 2 == 0 else col2
            item_qtys[item] = col.number_input(f"{item}", min_value=0, step=1, key=f"add_{item}")
        submitted = st.form_submit_button("Add Deposit(s)")
        if submitted and user:
            new_rows = []
            for item, qty in item_qtys.items():
                if qty > 0:
                    new_rows.append({"User": user.strip(), "Item": item, "Quantity": int(qty)})
            if new_rows:
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                save_data(df)
                st.success(f"Deposits added for {user}: " + ", ".join([f"{r['Quantity']}x {r['Item']}" for r in new_rows]))
                st.rerun()
            else:
                st.warning("Please enter at least one item with quantity > 0.")

st.markdown("---")

# ---- DEPOSITS OVERVIEW ----
st.header("Deposits Overview")

for cat, items in ORIGINAL_ITEM_CATEGORIES.items():
    color = CATEGORY_COLORS.get(cat, "#FFFFFF")
    st.markdown(f'<h2 style="color:{color}; font-weight:bold;">{cat}</h2>', unsafe_allow_html=True)
    # Calculate and sort item totals descending
    item_totals = []
    for item in items:
        total = df[(df["Item"] == item)]["Quantity"].sum()
        item_totals.append((item, total))
    item_totals.sort(key=lambda x: x[1], reverse=True)
    for item, total in item_totals:
        item_df = df[df["Item"] == item]
        target = targets[item]
        divine_val = divines[item]
        divine_total = (total / target * divine_val) if target > 0 else 0

        # INSTANT SELL SETTINGS
        instant_stack = stack_sizes.get(item, 50)
        sell_price = sell_prices.get(item, 0)
        instant_sell_price = sell_price / 2

        st.markdown(
            f"<div style='display:flex; align-items:center;'>"
            f"<b>{item}</b>: {total} / {target} "
            + (f"(Stack = {divine_val:.2f} Divines → Current Value ≈ {divine_total:.2f} Divines)" if divine_val > 0 else "")
            + f"&nbsp;&nbsp;<b style='margin-left:24px;'>Instant Sell ({instant_stack}):</b> <span style='color:orange;font-weight:bold;'>{instant_sell_price:.1f} Divines</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        st.progress(min(total / target, 1.0), text=f"{total}/{target}")

        # ---- Per-user breakdown & payout ----
        with st.expander("Per-user breakdown & payout", expanded=False):
            user_summary = (
                item_df.groupby("User")["Quantity"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            payouts = []
            fees = []
            for idx, row in user_summary.iterrows():
                qty = row["Quantity"]
                raw_payout = (qty / target) * divine_val if target else 0
                fee = math.floor((raw_payout * 0.10) * 10) / 10
                payout_after_fee = raw_payout - (raw_payout * 0.10)
                payout_final = math.floor(payout_after_fee * 10) / 10
                payouts.append(payout_final)
                fees.append(fee)
            user_summary["Fee (10%)"] = fees
            user_summary["Payout (Divines, after fee)"] = payouts
            st.dataframe(
                user_summary.style.format({"Fee (10%)": "{:.1f}", "Payout (Divines, after fee)": "{:.1f}"}),
                use_container_width=True
            )

st.markdown("---")

# ---- DELETE BUTTONS PER ROW (EDITORS ONLY), GROUPED BY ITEM ----
if st.session_state['is_editor']:
    st.header("Delete Deposits (permanently)")
    if len(df):
        for cat, items in ORIGINAL_ITEM_CATEGORIES.items():
            color = CATEGORY_COLORS.get(cat, "#FFFFFF")
            st.markdown(f'<h3 style="color:{color}; font-weight:bold;">{cat}</h3>', unsafe_allow_html=True)
            for item in items:
                item_rows = df[df["Item"] == item].reset_index()
                if not item_rows.empty:
                    st.markdown(f"**{item}**")
                    for i, row in item_rows.iterrows():
                        cols = st.columns([2, 2, 2, 1])
                        cols[0].write(row['User'])
                        cols[1].write(row['Item'])
                        cols[2].write(row['Quantity'])
                        delete_button = cols[3].button("Delete", key=f"delete_{row['index']}_{item}")
                        if delete_button:
                            df = df.drop(row['index']).reset_index(drop=True)
                            save_data(df)
                            st.success(f"Permanently deleted: {row['User']} - {row['Item']} ({row['Quantity']})")
                            st.rerun()
                else:
                    st.info(f"No deposits for {item}")
    else:
        st.info("No deposits yet!")
