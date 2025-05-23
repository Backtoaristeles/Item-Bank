# ... (keep all the setup/imports/loading as before!) ...

# ---- DEPOSITS OVERVIEW ----
st.header("Deposits Overview")

for cat, items in ORIGINAL_ITEM_CATEGORIES.items():
    color = CATEGORY_COLORS.get(cat, "#FFD700")
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

        # INSTANT SELL SETTINGS (per 1 item)
        stack_size = stack_sizes.get(item, 50)
        sell_price = float(sell_prices.get(item, 0))
        # Calculate instant sell for ONE item!
        if stack_size > 0:
            instant_sell_price_per_one = (sell_price / stack_size) * (instant_sell_percent / 100)
        else:
            instant_sell_price_per_one = 0

        st.markdown(
            f"<div style='display:flex; align-items:center;'>"
            f"<b>{item}</b>: {total} / {target} "
            + (f"(Stack = {divine_val:.2f} Divines → Current Value ≈ {divine_total:.2f} Divines)" if divine_val > 0 else "")
            + f"&nbsp;&nbsp;<b style='margin-left:24px;'>Instant Sell:</b> <span style='color:orange;font-weight:bold;'>{instant_sell_price_per_one:.3f} Divines per 1 {item}</span>"
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
            color = CATEGORY_COLORS.get(cat, "#FFD700")
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
