import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

# ----------- CONFIGURATION -----------
ADMIN_USER = "Admin"
ADMIN_PASS = "AdminPOEconomics"
FEE_WITHDRAW = 0.03
FEE_PROFIT = 0.02
START_DATE = date(2025, 5, 18)

# ----------- INITIAL STATE -----------
if "transactions" not in st.session_state:
    st.session_state["transactions"] = pd.DataFrame(
        columns=["Date", "User", "Type", "Amount"]
    )
if "nav" not in st.session_state:
    st.session_state["nav"] = {}  # date:str -> fund value (float)
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

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
            else:
                st.error("Falscher Benutzername oder Passwort.")

def admin_logout():
    st.session_state["is_admin"] = False
    st.info("Admin-Modus verlassen.")

# ----------- FUND SHARES MATH -----------
def recalculate_fund(transactions, nav_history):
    # 1. Find all dates
    all_dates = sorted(set(nav_history.keys()) | set(transactions["Date"].astype(str).unique()))
    if not all_dates:
        return {}, {}, {}, {}, {}, pd.DataFrame()
    # 2. For each day, track NAV, total shares, per-share price
    nav_per_share = {}
    total_shares = 0
    share_ledger = []  # [{user, date, type, amount, shares, nav_per_share}]
    user_shares_daily = {}  # user -> [shares held by date]
    user_shares = {}
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
                user_share_balances[u] = user_share_balances.get(u, 0.0) + shares
            elif ttype == "Withdrawal":
                shares = amt / nav_per_share_today if nav_per_share_today > 0 else 0
                shares = min(shares, user_share_balances.get(u, 0.0))
                amt = shares * nav_per_share_today
                total_shares -= shares
                user_share_balances[u] = user_share_balances.get(u, 0.0) - shares
                amt = -amt
            else:
                continue
            share_ledger.append({
                "Date": d_str, "User": u, "Type": ttype, "Amount": amt,
                "Shares": shares, "NAV/Share": nav_per_share_today
            })
        nav_per_share[d_str] = nav / total_shares if total_shares > 0 else 1.0
        for u in user_share_balances:
            if u not in user_shares_daily:
                user_shares_daily[u] = []
            user_shares_daily[u].append((d_str, user_share_balances[u]))
    # Current wallet value per user
    current_nav_share = nav_per_share.get(all_dates[-1], 1.0)
    user_shares = {u: user_share_balances[u] for u in user_share_balances}
    user_value = {u: user_shares[u] * current_nav_share for u in user_shares}
    # Deposited, withdrawn, profit, fees
    deposit_sum = transactions[transactions["Type"]=="Deposit"].groupby("User")["Amount"].sum().to_dict()
    withdrawal_sum = -transactions[transactions["Type"]=="Withdrawal"].groupby("User")["Amount"].sum().to_dict()
    profit = {u: user_value[u] - deposit_sum.get(u, 0.0) + withdrawal_sum.get(u, 0.0) for u in user_shares}
    after_fees = {}
    for u in user_shares:
        gross = user_value[u]
        withdrawal_fee = gross * FEE_WITHDRAW
        profit_fee = max(profit[u], 0) * FEE_PROFIT
        after_fees[u] = gross - withdrawal_fee - profit_fee
    ledger_df = pd.DataFrame(share_ledger)
    return nav_per_share, user_shares, user_value, after_fees, profit, ledger_df

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
    c1, c2, c3, c4 = st.columns([2,2,2,2])
    user = c1.text_input("User (Wallet)", "")
    ttype = c2.selectbox("Typ", ["Deposit", "Withdrawal"])
    amt = c3.number_input("Betrag (Divines)", min_value=0.01, step=0.01, value=10.0, format="%.2f")
    tx_date = c4.date_input("Datum", value=date.today(), min_value=START_DATE)
    submit = st.form_submit_button("Eintragen")
    if submit and user:
        tx = pd.DataFrame([[str(tx_date), user.strip(), ttype, amt]], columns=["Date","User","Type","Amount"])
        st.session_state["transactions"] = pd.concat([st.session_state["transactions"], tx], ignore_index=True)
        st.success(f"{'Einzahlung' if ttype=='Deposit' else 'Auszahlung'} für {user} eingetragen.")

st.markdown("### Fundwert pro Tag bearbeiten (NAV)")
today = date.today()
min_date = START_DATE
days_range = (today - min_date).days + 1
for i in range(days_range):
    d = min_date + timedelta(days=i)
    d_str = str(d)
    nav_val = st.session_state["nav"].get(d_str, 0.0)
    nav_input = st.number_input(f"{d} NAV (Gesamtwert Fund)", min_value=0.0, value=nav_val, step=0.01, format="%.2f", key=f"nav_{d_str}")
    st.session_state["nav"][d_str] = nav_input

if st.button("NAV speichern"):
    st.success("Fundwerte gespeichert!")

# ----------- HISTORY / LEDGER -----------
st.markdown("### Alle Transaktionen und Shares")
if ledger_df.empty:
    st.info("Noch keine Transaktionen durchgeführt.")
else:
    st.dataframe(ledger_df, use_container_width=True)

# ----------- EXPORT -----------
st.markdown("### Daten Exportieren")
st.download_button(
    label="Transaktionen als CSV herunterladen",
    data=st.session_state["transactions"].to_csv(index=False).encode(),
    file_name="fundbank_transactions.csv",
    mime="text/csv",
)
st.download_button(
    label="Fundwert (NAV) als CSV herunterladen",
    data=pd.DataFrame.from_dict(st.session_state["nav"], orient="index", columns=["NAV"]).to_csv().encode(),
    file_name="fundbank_nav.csv",
    mime="text/csv",
)
