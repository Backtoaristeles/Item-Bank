import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from google.oauth2.service_account import Credentials

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
ITEM_TARGET = 100
ALL_ITEMS = sum(ORIGINAL_ITEM_CATEGORIES.values(), [])
SHEET_NAME = "poe_item_bank"   # <-- Your Google Sheet name (NOT the file path, just the name)
SHEET_TAB = "Sheet1"           # <-- The exact name of your tab at the bottom (e.g., Sheet1 or Tabelle1)

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
        # Ensure columns exist
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

st.set_page_config(page_title="PoE Bulk Item Banking App", layout="wide")
st.title("PoE Bulk Item Banking App")

df = load_data()

# --- MULTI-ITEM DEPOSIT FORM ---
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
    st.subheader(cat)
    # Calculate and sort item totals descending
    item_totals = []
    for item in items:
        total = df[(df["Item"] == item)]["Quantity"].sum()
        item_totals.append((item, total))
    item_totals.sort(key=lambda x: x[1], reverse=True)
    for item, total in item_totals:
        item_df = df[df["Item"] == item]
        st.write(f"**{item}**: {total}")
        st.progress(min(total/ITEM_TARGET, 1.0), text=f"{total}/{ITEM_TARGET}")
        with st.expander("Per-user breakdown", expanded=False):
            user_summary = (
                item_df.groupby("User")["Quantity"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            st.table(user_summary)

st.markdown("---")

# ---- DELETE BUTTONS PER ROW ----
st.header("Delete Deposits (permanently)")

if len(df):
    st.write("Current Deposits (click Delete to permanently remove a row):")
    df_view = df.reset_index()  # includes index as a column
    for i, row in df_view.iterrows():
        cols = st.columns([2, 2, 2, 1])
        cols[0].write(row['User'])
        cols[1].write(row['Item'])
        cols[2].write(row['Quantity'])
        delete_button = cols[3].button("Delete", key=f"delete_{i}")
        if delete_button:
            df = df.drop(row['index']).reset_index(drop=True)
            save_data(df)
            st.success(f"Permanently deleted: {row['User']} - {row['Item']} ({row['Quantity']})")
            st.rerun()
else:
    st.info("No deposits yet!")
