import streamlit as st
import pandas as pd
import os

# ---- CONFIG ----
ITEM_CATEGORIES = {
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
ALL_ITEMS = sum(ITEM_CATEGORIES.values(), [])
ITEM_TARGET = 100  # Default target for progress bars

DATA_FILE = "bank_deposits.csv"

# ---- INITIALIZATION ----
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["User", "Item", "Quantity"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ---- MAIN APP ----
st.set_page_config(page_title="Item Banking App", layout="wide")
st.title("PoE Bulk Item Banking App")

df = load_data()

# Add Deposit
with st.form("deposit_form", clear_on_submit=True):
    st.subheader("Add a Deposit")
    user = st.text_input("User")
    item = st.selectbox("Item", ALL_ITEMS)
    qty = st.number_input("Quantity", min_value=1, step=1)
    submitted = st.form_submit_button("Add Deposit")
    if submitted and user and item and qty:
        new_row = {"User": user.strip(), "Item": item, "Quantity": int(qty)}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success(f"Added {qty} x {item} for {user}")

st.markdown("---")

# Grouped Display with Progress Bars and per-user breakdown
st.header("Deposits Overview")

for cat, items in ITEM_CATEGORIES.items():
    st.subheader(cat)
    for item in items:
        item_df = df[df["Item"] == item]
        total = item_df["Quantity"].sum()
        bar_color = "green" if total >= ITEM_TARGET else "blue"
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
st.header("Edit or Delete Deposits")

if len(df):
    # Show editable table
    df_view = df.copy()
    df_view.index = df_view.index + 1  # 1-based index for user-friendliness
    st.dataframe(df_view)
    idx = st.number_input("Row number to edit/delete (as shown above)", min_value=1, max_value=len(df), step=1)
    action = st.selectbox("Action", ["Edit", "Delete"])
    if st.button("Apply Action"):
        row_idx = idx - 1
        if action == "Delete":
            df = df.drop(df.index[row_idx]).reset_index(drop=True)
            save_data(df)
            st.success("Deleted row.")
            st.experimental_rerun()
        elif action == "Edit":
            row = df.iloc[row_idx]
            st.info(f"Editing row {idx}")
            with st.form("edit_form"):
                new_user = st.text_input("User", value=row["User"])
                new_item = st.selectbox("Item", ALL_ITEMS, index=ALL_ITEMS.index(row["Item"]))
                new_qty = st.number_input("Quantity", min_value=1, value=int(row["Quantity"]), step=1)
                confirm = st.form_submit_button("Save Edit")
                if confirm:
                    df.at[row_idx, "User"] = new_user.strip()
                    df.at[row_idx, "Item"] = new_item
                    df.at[row_idx, "Quantity"] = int(new_qty)
                    save_data(df)
                    st.success("Row edited.")
                    st.experimental_rerun()
else:
    st.info("No deposits yet!")

