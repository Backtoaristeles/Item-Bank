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
    "White Item Bases": [
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
    "White Item Bases": "#FFFFFF",      # White
    "Tablets": "#AA66CC",     # Purple
    "Various": "#42A5F5",     # Blue
}

ITEM_COLORS = {
    "Breach ring level 82": "#D6A4FF",   # purple
    "Stellar Amulet": "#FFD700",         # gold/yellow
    "Heavy Belt": "#A4FFA3",             # greenish
    "Waystone EXP + Delirious": "#FF6961",
    "Waystone EXP 35%": "#FFB347",
    "Waystone EXP": "#FFB347",
    "Tablet Exp 9%+10% (random)": "#7FDBFF",
    "Quantity Tablet (6%+)": "#B0E0E6",
    "Grand Project Tablet": "#FFDCB9",
    "Logbook level 79-80": "#42A5F5",
}
def get_item_color(item):
    return ITEM_COLORS.get(item, "#FFF")

SHEET_NAME = "poe_item_bank"
SHEET_TAB = "Sheet1"
TARGETS_TAB = "Targets"

DEFAULT_BANK_BUY_PCT = 80   # percent

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

def load_targets():
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet(TARGETS_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=TARGETS_TAB, rows=50, cols=4)
        ws.append_row(["Item", "Target", "Divines", "Link"])
    df = get_as_dataframe(ws, evaluate_formulas=True, dtype=str).dropna(how='all')
    targets = {}
    divines = {}
    links = {}
    if not df.empty and "Item" in df.columns:
        if "Target" not in df.columns:
            df["Target"] = 100
        if "Divines" not in df.columns:
            df["Divines"] = ""
        if "Link" not in df.columns:
            df["Link"] = ""
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
            try:
                links[item] = row["Link"]
            except Exception:
                links[item] = ""
    for item in ALL_ITEMS:
        if item not in targets:
            targets[item] = 100
        if item not in divines:
            divines[item] = 0
        if item not in links:
            links[item] = ""
    return targets, divines, links, ws

def save_targets(targets, divines, links, ws):
    df = pd.DataFrame([{"Item": item, "Target": targets[item], "Divines": divines[item], "Link": links[item]} for item in ALL_ITEMS])
    ws.clear()
    set_with_dataframe(ws, df, include_index=False)

def save_data(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet(SHEET_TAB)
    set_with_dataframe(sheet, df[["User", "Item", "Quantity"]], include_index=False)

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
targets, divines, links, ws_targets = load_targets()

# ---- SETTINGS SIDEBAR ----
with st.sidebar:
    st.header("Per-Item Targets & Divine Value")

    # Only admins see and can set the Bank Buy %
    if st.session_state['is_editor']:
        if 'bank_buy_pct' not in st.session_state:
            st.session_state['bank_buy_pct'] = DEFAULT_BANK_BUY_PCT

        st.subheader("Bank Instant Buy Settings")
        bank_buy_pct = st.number_input(
            "Bank buy % of sell price (instant sell payout)",
            min_value=10, max_value=100, step=1,
            value=st.session_state['bank_buy_pct'],
            key="bank_buy_pct_input"
        )
        if bank_buy_pct != st.session_state['bank_buy_pct']:
            st.session_state['bank_buy_pct'] = bank_buy_pct
            st.success("Bank buy % updated. All instant sell prices are now updated.")

        changed = False
        new_targets = {}
        new_divines = {}
        new_links = {}
        st.subheader("Edit Targets, Values, and Trade Links")
        for item in ALL_ITEMS:
            cols = st.columns([2, 2])
            tgt = cols[0].number_input(
                f"{item} target",
                min_value=1,
                value=int(targets.get(item, 100)),
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
            link = st.text_input(
                f"{item} trade link",
                value=links.get(item, ""),
                key=f"link_{item}"
            )
            if tgt != targets[item] or div != divines[item] or link != links[item]:
                changed = True
            new_targets[item] = tgt
            new_divines[item] = div
            new_links[item] = link
        if st.button("Save Targets, Values, and Links") and changed:
            save_targets(new_targets, new_divines, new_links, ws_targets)
            st.success("Targets, Divine values, and Trade Links saved! Refresh the page to see updates.")
            st.stop()
    else:
        for item in ALL_ITEMS:
            stack = divines[item]
            target = targets[item]
            trade_link = links.get(item, "")
            st.markdown(
                f"""<div style='margin-bottom:6px;'>
                    <span style='font-weight:bold;'>{item}:</span><br>
                    <span style='background: #222; color: #ffe066; border-radius: 6px; padding: 2px 10px; font-weight: 600;'>[Stack = {stack:.2f} Divines]</span>
                    <span style='color:#ccc; margin-left:8px;'>Target = {target}</span><br>
                    {("Trade Link: <a href='" + trade_link + "' target='_blank'>[Open]</a><br>") if trade_link else ""}
                </div>""",
                unsafe_allow_html=True
            )

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

bank_buy_pct = st.session_state.get('bank_buy_pct', DEFAULT_BANK_BUY_PCT)

for cat, items in ORIGINAL_ITEM_CATEGORIES.items():
    color = CATEGORY_COLORS.get(cat, "#FFD700")
    st.markdown(f"""
    <div style='margin-top: 38px;'></div>
    <h2 style="color:{color}; font-weight:bold; margin-bottom: 14px;">{cat}</h2>
    """, unsafe_allow_html=True)
    # Calculate and sort item totals descending
    item_totals = []
    for item in items:
        total = df[(df["Item"] == item)]["Quantity"].sum()
        item_totals.append((item, total))
    item_totals.sort(key=lambda x: x[1], reverse=True)
    for item, total in item_totals:
        item_color = get_item_color(item)
        item_df = df[df["Item"] == item]
        target = targets[item]
        divine_val = divines[item]
        divine_total = (total / target * divine_val) if target > 0 else 0
        # Calculate instant sell price for ONE item
        if target > 0:
            instant_sell_price = (divine_val / target) * bank_buy_pct / 100
        else:
            instant_sell_price = 0

        link_html = ""
        if links.get(item, ""):
            link_html = f"<a href='{links[item]}' target='_blank' style='margin-left:22px; color:#4af;'>🔗 Trade Link</a>"

        # -- HIGHLIGHTED BADGE AND INFO --
        if divine_val > 0 and target > 0:
            current_value = divine_total
            extra_info = (
                f"<span style='margin-left:22px; color:#AAA;'>"
                f"<span style='background: #292900; color:#ffe066; border-radius: 8px; padding: 4px 10px; font-weight: 600;'>"
                f"Instant Sell: {instant_sell_price:.3f} Divines <span style='font-size:85%; color:#888;'>(per item)</span>"
                f"</span>"
                f"</span>"
                f"<br>"
                f"<span style='display: inline-block; margin-left:22px; font-size:95%;'>"
                f"<span style='background: #222; color: #ffe066; border-radius: 6px; padding: 2px 10px; font-weight: 600;'>[Stack = {divine_val:.2f} Divines]</span>"
                f"<span style='color:#ccc; margin-left:12px;'>→ Current Value: {current_value:.2f} Divines</span>"
                f"</span>"
            )
        elif divine_val > 0:
            extra_info = (
                f"<span style='margin-left:22px; color:#AAA;'>"
                f"<span style='background: #222; color: #ffe066; border-radius: 6px; padding: 2px 10px; font-weight: 600;'>[Stack = {divine_val:.2f} Divines]</span>"
                f"</span>"
            )
        else:
            extra_info = ""

        st.markdown(
            f"""
            <div style='
                display:flex; 
                flex-direction:column;
                align-items:flex-start; 
                border: 2px solid #222; 
                border-radius: 10px; 
                margin: 8px 0 16px 0; 
                padding: 10px 18px;
                background: #181818;
            '>
                <span style='font-weight:bold; color:{item_color}; font-size:1.18em; letter-spacing:0.5px;'>
                    [{item}]
                </span>
                <span style='margin-left:0px; font-size:1.12em; color:#FFF;'>
                    <b>Deposited:</b> {total} / {target}
                </span>
                {extra_info}
                {link_html}
            </div>
            """,
            unsafe_allow_html=True
        )

        # GREEN BAR IF FULL, ELSE NORMAL
        if total >= target:
            st.success(f"✅ {total}/{target} – Target reached!")
            st.markdown("""
            <div style='height:22px; width:100%; background:#22c55e; border-radius:7px; display:flex; align-items:center;'>
                <span style='margin-left:10px; color:white; font-weight:bold;'>FULL</span>
            </div>
            """, unsafe_allow_html=True)
        else:
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

# ---- DELETE BUTTONS PER ROW (EDITORS ONLY), GROUPED BY ITEM IN EXPANDERS ----
if st.session_state['is_editor']:
    st.header("Delete Deposits (permanently)")
    if len(df):
        for cat, items in ORIGINAL_ITEM_CATEGORIES.items():
            color = CATEGORY_COLORS.get(cat, "#FFD700")
            st.markdown(f'<h3 style="color:{color}; font-weight:bold;">{cat}</h3>', unsafe_allow_html=True)
            cols = st.columns(len(items))
            for idx, item in enumerate(items):
                item_rows = df[df["Item"] == item].reset_index()
                with cols[idx]:
                    with st.expander(f"{item} ({len(item_rows)} deposits)", expanded=False):
                        if not item_rows.empty:
                            for i, row in item_rows.iterrows():
                                c = st.columns([2, 2, 2, 1])
                                c[0].write(row['User'])
                                c[1].write(row['Item'])
                                c[2].write(row['Quantity'])
                                delete_button = c[3].button("Delete", key=f"delete_{row['index']}_{item}")
                                if delete_button:
                                    df = df.drop(row['index']).reset_index(drop=True)
                                    save_data(df)
                                    st.success(f"Permanently deleted: {row['User']} - {row['Item']} ({row['Quantity']})")
                                    st.rerun()
                        else:
                            st.info("No deposits for this item.")
    else:
        st.info("No deposits yet!")
