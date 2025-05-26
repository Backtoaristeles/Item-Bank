import streamlit as st
import pandas as pd
import numpy as np
import uuid
import time
from datetime import date, timedelta
import matplotlib.pyplot as plt

# ----------- CONFIGURATION -----------
ADMIN_USER = "Admin"
ADMIN_PASS = "AdminPOEconomics"
FEE_WITHDRAW = 0.03
FEE_PROFIT = 0.02
START_DATE = date(2025, 5, 18)

# ----------- INITIAL STATE -----------
if "transactions" not in st.session_state:
    st.session_state["transactions"] = pd.DataFrame(
        columns=["Date", "User", "Item", "Type", "Amount", "TxID", "Timestamp"]
    )
if "nav" not in st.session_state:
    st.session_state["nav"] = {}
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "logs" not in st.session_state:
    st.session_state["logs"] = []

# ----------- AUTH -----------
def admin_login():
    with st.form("admin_login_form", clear_on_submit=True):
        st.write("🔑 **Admin Login**")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if user == ADMIN_USER and pw == ADMIN_PASS:
                st.session_state["is_admin"] = True
                st.success("Admin-Modus aktiviert.")
                st.session_state["logs"].append(f"✅ Admin {user} logged in.")
            else:
                st.error("Falscher Benutzername oder Passwort.")

def admin_logout():
    st.session_state["is_admin"] = False
    st.info("Admin-Modus verlassen.")
    st.session_state["logs"].append("ℹ️ Admin logged out.")

# ----------- FUND SHARES MATH -----------
def recalculate_fund(transactions, nav_history):
    all_dates = sorted(set(nav_history.keys()) | set(transactions["Date"].astype(str).unique()))
    if not all_dates:
        return {}, {}, {}, {}, {}, pd.DataFrame()
    nav_per_share = {}
    total_shares = 0
    share_ledger = []
    user_share_balances = {u: 0.0 for u in transactions["User"].unique()}
    for d in all_dates:
        d_str = str(d)
        nav = float(nav_history.get(d_str, np.nan))
        txs_today = transactions[transactions["Date"].astype(str) == d_str]
        nav_per_share_today = nav / total_shares if total_shares > 0 else 1.0
        for i, row in txs_today.iterrows():
            amt = float(row["Amount"])
            u = row["User"]
            ttype = row["Type"]
            if ttype == "Deposit":
                shares = amt / nav_per_share_today if nav_per_share_today > 0 else 0
                total_shares += shares
                user_share_balances[u] += shares
            elif ttype == "Withdrawal":
                shares = amt / nav_per_share_today if nav_per_share_today > 0 else 0
                shares = min(shares, user_share_balances[u])
                amt = shares * nav_per_share_today
                total_shares -= shares
                user_share_balances[u] -= shares
                amt = -amt
            share_ledger.append({
                "Date": d_str, "User": u, "Item": row["Item"], "Type": ttype, "Amount": amt,
                "Shares": shares, "NAV/Share": nav_per_share_today
            })
        nav_per_share[d_str] = nav / total_shares if total_shares > 0 else 1.0
    current_nav_share = nav_per_share.get(all_dates[-1], 1.0)
    user_value = {u: user_share_balances[u] * current_nav_share for u in user_share_balances}
    deposit_sum = transactions[transactions["Type"] == "Deposit"].groupby("User")["Amount"].sum().to_dict()
    withdrawal_sum = -transactions[transactions["Type"] == "Withdrawal"].groupby("User")["Amount"].sum().to_dict()
    profit = {u: user_value[u] - deposit_sum.get(u, 0.0) + withdrawal_sum.get(u, 0.0) for u in user_share_balances}
    after_fees = {}
    for u in user_share_balances:
        gross = user_value[u]
        withdrawal_fee = gross * FEE_WITHDRAW
        profit_fee = max(profit[u], 0) * FEE_PROFIT
        after_fees[u] = gross - withdrawal_fee - profit_fee
    ledger_df = pd.DataFrame(share_ledger)
    return nav_per_share, user_share_balances, user_value, after_fees, profit, ledger_df

# ----------- APP HEADER -----------
st.set_page_config("Bank Fund Shares Tracker", layout="wide")
st.title("💎 FundBank — Fair Shares Tracking")

st.markdown("""
**Wallet-Übersicht**  
(Admins können Einzahlungen, Auszahlungen & Fundwert bearbeiten, User nur einsehen.)
""")

# ----------- WALLET TABLE -----------
nav_per_share, user_shares, user_value, after_fees, profit, ledger_df = recalculate_fund(
    st.session_state["transactions"], st.session_state["nav"]
)

wallet_data = pd.DataFrame([
    {
        "User": u,
        "Shares": user_shares[u],
        "Wallet (Divines)": user_value[u],
        "After Fees": after_fees[u],
        "Profit": profit[u]
    } for u in user_value
])

if not wallet_data.empty and "Wallet (Divines)" in wallet_data.columns:
    wallet_data = wallet_data.sort_values("Wallet (Divines)", ascending=False)

st.header("Alle Wallets (heute)")
if wallet_data.empty:
    st.info("Noch keine Einzahlungen oder NAV-Daten eingetragen.")
else:
    st.dataframe(wallet_data.style.format({
        "Shares": "{:.4f}",
        "Wallet (Divines)": "{:.2f}",
        "After Fees": "{:.2f}",
        "Profit": "{:.2f}",
    }), use_container_width=True)

# ----------- USER FILTER -----------
st.markdown("### Benutzer-Filter")
selected_user = st.selectbox("Wähle einen Benutzer aus, um nur dessen Verlauf zu sehen:", ["<Alle>"] + sorted(st.session_state["transactions"]["User"].unique()))
if selected_user != "<Alle>":
    user_tx = st.session_state["transactions"][st.session_state["transactions"]["User"] == selected_user]
    st.write(f"**Transaktionen für {selected_user}:**")
    st.dataframe(user_tx, use_container_width=True)

# ----------- ADMIN LOGIN -----------
if not st.session_state["is_admin"]:
    with st.expander("🔒 Admin Login"):
        admin_login()
    st.stop()

# ----------- ADMIN CONTROLS -----------
col1, col2 = st.columns([2, 1])
with col2:
    if st.button("Admin Logout"):
        admin_logout()
        st.experimental_rerun()
st.success("Admin-Modus: Volle Kontrolle freigeschaltet.")

st.markdown("### Neue Einzahlung oder Auszahlung")
with st.form("add_tx", clear_on_submit=True):
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
    user = c1.text_input("User (Wallet)", "")
    item = c2.text_input("Item", "")
    ttype = c3.selectbox("Typ", ["Deposit", "Withdrawal"])
    amt = c4.number_input("Betrag (Divines)", min_value=0.01, step=0.01, value=10.0, format="%.2f")
    tx_date = c5.date_input("Datum", value=date.today(), min_value=START_DATE)
    submit = st.form_submit_button("Eintragen")
    if submit and user and item:
        tx_id = str(uuid.uuid4())
        timestamp = time.time()
        tx = pd.DataFrame([[str(tx_date), user.strip(), item.strip(), ttype, amt, tx_id, timestamp]],
                          columns=["Date", "User", "Item", "Type", "Amount", "TxID", "Timestamp"])
        existing = st.session_state["transactions"]
        dupe_check = existing[
            (existing["Date"] == str(tx_date)) &
            (existing["User"] == user.strip()) &
            (existing["Item"] == item.strip()) &
            (existing["Type"] == ttype) &
            (existing["Amount"] == amt)
        ]
        if not dupe_check.empty:
            st.warning("⚠️ Achtung: Eine identische Transaktion existiert bereits! Wird trotzdem hinzugefügt.")
            st.session_state["logs"].append(f"⚠️ Dupe detected: {user} {item} {ttype} {amt} on {tx_date}")
        st.session_state["transactions"] = pd.concat([existing, tx], ignore_index=True)
        st.session_state["logs"].append(f"✅ Transaction added: {user} {item} {ttype} {amt} on {tx_date}")
        st.success(f"{'Einzahlung' if ttype == 'Deposit' else 'Auszahlung'} für {user} ({item}) eingetragen.")

if st.button("Letzte Transaktion rückgängig machen"):
    if not st.session_state["transactions"].empty:
        last_row = st.session_state["transactions"].iloc[-1]
        st.session_state["transactions"] = st.session_state["transactions"].iloc[:-1]
        st.session_state["logs"].append(f"↩️ Letzte Transaktion rückgängig gemacht: {last_row['User']} {last_row['Item']} {last_row['Type']} {last_row['Amount']}")
        st.success("Letzte Transaktion wurde entfernt.")
    else:
        st.warning("Keine Transaktionen zum Rückgängig machen.")

# ----------- CHARTS -----------
st.markdown("### 📊 Trends und Diagramme")
if not st.session_state["transactions"].empty:
    per_item = st.session_state["transactions"].groupby("Item")["Amount"].sum()
    per_user = st.session_state["transactions"].groupby("User")["Amount"].sum()

    fig1, ax1 = plt.subplots()
    per_item.plot(kind="bar", ax=ax1)
    ax1.set_title("Gesamtbetrag pro Item")
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots()
    per_user.plot(kind="bar", ax=ax2)
    ax2.set_title("Gesamtbetrag pro Benutzer")
    st.pyplot(fig2)

# ----------- EXPORT -----------
st.markdown("### Daten Exportieren")
# Full transactions export
st.download_button(
    label="Transaktionen als CSV herunterladen",
    data=st.session_state["transactions"].to_csv(index=False).encode(),
    file_name="fundbank_transactions.csv",
    mime="text/csv",
)
# Backend-compatible (aggregated) export
backend_data = st.session_state["transactions"].groupby(
    ["User", "Item"]
)["Amount"].sum().reset_index()
backend_data.rename(columns={"Amount": "Quantity"}, inplace=True)
st.download_button(
    label="Export Backend Data (User-Item-Quantity)",
    data=backend_data.to_csv(index=False).encode(),
    file_name="fundbank_backend_export.csv",
    mime="text/csv",
)

# ----------- ADMIN LOGS -----------
st.markdown("### 📝 Admin Logs")
if st.session_state["logs"]:
    for log_entry in reversed(st.session_state["logs"][-20:]):
        st.text(log_entry)
else:
    st.info("Keine Admin-Aktionen bisher protokolliert.")
