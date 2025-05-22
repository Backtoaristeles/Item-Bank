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
ITEM_TARGET = 100

DATA_FILE = "bank_deposits.csv"

# ---- DATA HANDLING ----
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=["User", "Item", "Quantity"])
    return pd.DataFrame(columns=["User", "Item", "Quantity"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ---- MAIN APP ----
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
        item_qtys[item] = col.number_input(f"{item}", min_value=0, step=1, key=item)
    submitted = st.form_submit_button("Add Deposit(s)")
    if submitted and user:
        new_rows = []
        for item, qty in item_qtys.items():
            if qty > 0:
                new_rows.append({"User": user.strip(), "Item": item, "Quantity": int(qty)})
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            save_data(df)
            st.success(f"Added deposits for {user}: " + ", ".join([f"{r['Quantity']}x {r['Item']}" for r in new_rows]))
        else:
            st.warning("Please enter at least one item with quantity > 0.")

st.markdown("---")

# ---- DEPOSITS OVERVIEW ----
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
    df_view = df.copy()
    df_view.index = df_view.index + 1  # 1-based for user
    st.dataframe(df_view)
    idx = st.number_input("Row number to edit/delete (see table above)", min_value=1, max_value=len(df), step=1)
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
                new_user = st.text_input("User", value=row["User"], key="edit_user")
                new_item = st.selectbox("Item", ALL_ITEMS, index=ALL_ITEMS.index(row["Item"]), key="edit_item")
                new_qty = st.number_input("Quantity", min_value=1, value=int(row["Quantity"]), step=1, key="edit_qty")
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

