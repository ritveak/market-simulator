"""Market Simulator - Streamlit App."""
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from src.data.loader import discover_csv_files, load_price_data, load_price_data_from_upload
from src.engine.simulator import run_simulation, SimulatorConfig
from src.strategies.base import SimulationResult

# Color scheme for strategies and their deployment popups
STRATEGY_COLORS = {
    "SIP": "#1f77b4",
    "The Genie": "#ff7f0e",
    "Staggered Tactician": "#2ca02c",
}
GENIE_HOVER_COLOR = "#e65100"   # Dark orange for Genie popup text
STAGGERED_HOVER_COLOR = "#1b5e20"  # Dark green for Staggered popup text
SIP_HOVER_COLOR = "#0d47a1"  # Dark blue for SIP popup text

# Page config
st.set_page_config(page_title="Market Simulator", layout="wide")

# Connect section (update with your URLs)
LINKEDIN_URL = "https://www.linkedin.com/in/ritveak/"
LINKEDIN_POST_URL = "https://www.linkedin.com/posts/your-post-id"  # Post about motivation & story

# Get more: GitHub repository URL
GITHUB_REPO_URL = "https://github.com/yourusername/market-simulator"

# Understand me dialog: YouTube video ID (from https://www.youtube.com/watch?v=VIDEO_ID)
YOUTUBE_VIDEO_ID = "Ol18JoeXlVI"

# Info tooltips for each input
INFO = {
    "data_file": "Select a CSV file from the resources folder. Files must have Date (DD/MM/YY) and Close columns.",
    "initial_capital": "Starting cash balance before any contributions. Add if you already have savings to invest.",
    "monthly_contribution": "Amount added to your savings bucket each month. Same for all three strategies for fair comparison.",
    "liquid_fund_yield": "Annual interest rate (%) earned on cash before deployment. Applies to non-deployed savings only.",
    "genie_window": "Time period for each deployment cycle. Cash accumulates, then 100% is deployed on the lowest-price day in that window.",
    "simulation_dates": "Date range for backtesting. Must fall within the selected data file's date range.",
    "staggered_rules": "Map market drop % to deployment %. E.g. 2% drop → deploy 10% of remaining cash (not the cash at all-time high). Highest matching rule applies per day.",
    "staggered_drop_from": "All-time high: drop measured from last high (can deploy every day if price stays flat). Last purchase: drop measured from last deployment price (avoids repeated deployment when flat); first deployment uses all-time high; if price makes new all-time high above last purchase, drop is measured from that high.",
}


def build_snapshot(selected_label, start_date, end_date, monthly_contribution, liquid_fund_yield,
                   initial_capital, genie_value, genie_unit, staggered_drop_from, staggered_df) -> dict:
    """Build a JSON-serializable snapshot of current inputs."""
    rules = [{"Market Drop %": float(r["Market Drop %"]), "Deployment %": float(r["Deployment %"])}
             for _, r in staggered_df.iterrows()]
    return {
        "data_file": selected_label,
        "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),
        "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
        "monthly_contribution": float(monthly_contribution),
        "liquid_fund_yield": float(liquid_fund_yield),
        "initial_capital": float(initial_capital),
        "genie_window_value": int(genie_value),
        "genie_window_unit": str(genie_unit),
        "staggered_drop_from": str(staggered_drop_from),
        "staggered_rules": rules,
    }


def apply_snapshot(snapshot: dict, labels: list, date_min, date_max) -> tuple[bool, str]:
    """Apply snapshot to session state. Returns (success, error_message)."""
    try:
        data_file = snapshot.get("data_file")
        if data_file not in labels:
            data_file = labels[0] if labels else ""
        st.session_state["data_file"] = data_file

        start = snapshot.get("start_date")
        end = snapshot.get("end_date")
        if start:
            d = pd.to_datetime(start).date() if isinstance(start, str) else start
            st.session_state["start_dt"] = d
        if end:
            d = pd.to_datetime(end).date() if isinstance(end, str) else end
            st.session_state["end_dt"] = d

        st.session_state["monthly_contribution"] = float(snapshot.get("monthly_contribution", 10000))
        st.session_state["liquid_fund_yield"] = float(snapshot.get("liquid_fund_yield", 6))
        st.session_state["initial_capital"] = float(snapshot.get("initial_capital", 0))
        st.session_state["genie_val"] = int(snapshot.get("genie_window_value", 6))
        st.session_state["genie_unit"] = str(snapshot.get("genie_window_unit", "months"))
        drop_from = snapshot.get("staggered_drop_from", "All-time high")
        if drop_from in ("ath", "last_purchase"):
            drop_from = "All-time high" if drop_from == "ath" else "Last purchase"
        st.session_state["staggered_drop_from"] = str(drop_from)

        rules = snapshot.get("staggered_rules", [{"Market Drop %": 2, "Deployment %": 10}])
        if rules and ("Market Drop %" not in rules[0] if rules[0] else True):
            rules = [{"Market Drop %": float(r.get("drop_pct", 2)), "Deployment %": float(r.get("deploy_pct", 10))} for r in rules]
        # data_editor forbids session_state writes; use separate key and pass as initial data
        st.session_state["_staggered_restored"] = pd.DataFrame(rules) if rules else pd.DataFrame({"Market Drop %": [2], "Deployment %": [10]})
        return True, ""
    except Exception as e:
        return False, str(e)


# --- Understand me dialog (modal with scrollable content) ---
@st.dialog("Understand Market Simulator — Complete Guide", width="large")
def show_understand_dialog():
    """Scrollable modal explaining the project in depth."""
    st.markdown("**Either watch the video or read through the guide below.**")
    if YOUTUBE_VIDEO_ID:
        st.components.v1.html(
            f'<iframe width="100%" height="400" src="https://www.youtube.com/embed/{YOUTUBE_VIDEO_ID}" '
            'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
            'allowfullscreen></iframe>',
            height=420,
        )
    st.markdown("---")
    content = """
## 🎯 Intent

**Market Simulator** is a backtesting tool that helps you compare three different investment strategies using the same cash inflow and index price data. The goal is to answer: *"How would my money have performed if I had followed SIP vs timing-based approaches?"*

All three strategies receive the same monthly contribution and use the same price series, so the comparison is fair and apples-to-apples.

---

## 🔄 Deployment Strategy (All Three)

### 1. SIP (Systematic Investment Plan) — Blue

- **Intent**: The boring, non-indulgent, set-up-and-forget intent.
- **Logic**: Deploy a **fixed amount** (monthly contribution + any initial capital) on the **first trading day of each month**.
- **No liquid fund**: Cash does not earn interest; it is deployed immediately at month start.
- **Fair comparison**: Same total amount is invested as the other strategies over time; timing is the only difference.

### 2. The Genie — Orange

- **Intent**: Imagine you can predict and time the market like a genie—you intend to buy at the extreme lowest point in a particular window, and you earn a stable fixed return on parked cash until you deploy all your savings.
- **Logic**: Credit full monthly contribution at month start. Cash sits in a **liquid fund** (compounds daily). Within each **time window** (e.g. 6 months), deploy **100% of accumulated cash** on the **single day with the lowest closing price** in that window.
- **Effect**: Tries to time the bottom within each cycle.

### 3. Staggered Tactician — Green

- **Intent**: Someone who finds SIP boring and wants to try lumpsum investment in a staggered way.
- **Logic**: Credit full monthly contribution at month start. Cash compounds daily in the liquid fund.
- **All-time high price**: Track the last high; update only when price makes a new high.
- **Deployment**: When price drops from the reference (all-time high or last purchase) by X% (per your rules), deploy Y% of **remaining cash**. Highest matching rule wins each day.
- **Drop-from reference**: Choose **All-time high** (can deploy every day if price stays flat) or **Last purchase** (avoids repeated deployment when flat; first deployment uses all-time high; if price makes new all-time high above last purchase, drop is measured from that high).
- **Example**: 2% drop → deploy 10% of remaining cash; 5% drop → 20%; 10% drop → 50%.

---

## 📥 Input Fields

### Global (applies to all strategies)

| Field | Purpose |
|-------|---------|
| **Data File** | Select which CSV to use. Files are discovered from `resources/` (e.g. Nifty 50). Each file must have **Date** and **Close** columns. |
| **Simulation Start / End** | Date range for backtesting. Must fall within the selected file's date range. |
| **Monthly Contribution (₹)** | Amount added to savings at the start of each month. Same for all three strategies. |
| **Liquid Fund Yield (% annual)** | Interest rate on cash before deployment. Genie and Tactician park cash here; SIP does not use this. |
| **Initial Capital (₹)** | Starting balance (e.g. existing savings) invested on day one. |

### The Genie (orange section)

| Field | Purpose |
|-------|---------|
| **Genie Window (value + unit)** | Length of each deployment cycle (e.g. 6 months). Cash accumulates during the window, then 100% is deployed on the **lowest-price day** in that window. |

### Staggered Tactician (green section)

| Field | Purpose |
|-------|---------|
| **Invest Y% when price falls X% from** | **All-time high** (default): drop measured from last high—can deploy every day if price stays flat. **Last purchase**: drop measured from last deployment price—avoids repeated deployment when flat; first deployment uses all-time high; if price makes new all-time high above last purchase, drop is measured from that high. |
| **Market Drop %** | Threshold drop from the reference (all-time high or last purchase) to trigger deployment. |
| **Deployment %** | Percentage of **remaining cash** (not the cash at the reference) to deploy when the threshold is met. Highest matching rule applies per day. |

---

## 📂 How Data Is Sourced

- **Location**: CSV files under the `resources/` folder. The app scans **recursively**—any CSV in `resources/` or its subfolders is discovered. Add more files and they appear in the **Data File** dropdown.
- **Currently available**: Nifty 50 historical data (2007–2026). Path: `resources/nsedata/nifty/nifty2007-2026.csv`. Date and closing price only.
- **Format**: Each CSV must have exactly two columns:
  - **Date** — format `DD/MM/YY` (day/month/year)
  - **Close** — closing price for that trading day
- **Usage**: The simulator uses closing prices day-by-day. No other columns are used. Ensure there are no gaps or invalid rows.

---

## 📈 All-time Highs (Staggered Tactician)

An **all-time high** is a day when the index makes a **new high** (closing price is strictly above the previous high).

- The strategy tracks the **all-time high price** (the last high).
- It updates only when price goes **above** that level.
- **Drop from all-time high** = `(ath_price - current_price) / ath_price × 100` (in %).
- **Last purchase option**: When enabled, drop is measured from the last deployment price instead of all-time high. This avoids deploying every day when price flatlines after a drop. First deployment uses all-time high; if price makes a new all-time high above your last purchase, the reference switches back to all-time high.
- On the chart, all-time highs are shown as **green triangle-up markers** on the Close Price line (right axis). Toggle with *"All-time highs"*.

---

## ❌ Red Cross (No Cash Left)

A **red cross** on a Staggered Tactician deployment point means:

> **"The drop-from-all-time-high rule was met, but there was effectively no cash left to deploy."**

- Cash had fallen below ₹1 (or was 0).
- The strategy would have deployed per the rules, but it had nothing meaningful to invest.
- Hover shows: *"Drop from all-time high: X.X%"* and *"No cash left"*.

---

## 📊 Chart & Metrics

- **Left Y-axis**: Portfolio value (₹) for each strategy.
- **Right Y-axis**: Index closing price.
- **Dots**: Deployment points (green circles for normal Tactician, red crosses for "no cash left").
- **Metrics**: Total invested, final value, XIRR, max drawdown, cash balance.

---

## 📋 Snapshot / Restore

Use the **Snapshot / Restore inputs** expander in the sidebar to save and replay scenarios:

- **Snapshot**: Current inputs are shown as JSON. Copy, or download as a file.
- **Paste & Apply**: Paste JSON into the box and click **Apply pasted** to restore inputs.
- **Upload JSON**: Upload a previously saved `.json` file to restore a scenario.
"""
    st.markdown(content)
    if st.button("Close", key="understand_close"):
        st.rerun()


@st.dialog("Upload my data", width="large")
def show_upload_data_dialog():
    """Dialog for uploading a CSV with format instructions."""
    st.markdown("""
    **Upload your CSV file** with the correct format:

    - **First column**: `Date` — dates in **MM/DD/YY** format (e.g. 01/15/24 for Jan 15, 2024)
    - **Second column**: `Close` — closing price for each trading day

    Only these two columns are required. Other columns will be ignored.
    """)
    st.markdown("---")
    uploaded = st.file_uploader("Choose CSV file", type=["csv"], key="upload_data_file")
    if uploaded is not None:
        try:
            df = load_price_data_from_upload(uploaded)
            if len(df) == 0:
                st.error("No valid rows found. Check that dates are in MM/DD/YY format.")
            else:
                st.session_state["_uploaded_df"] = df
                st.session_state["_uploaded_filename"] = uploaded.name
                st.session_state["_use_uploaded_data"] = True
                st.success(f"Loaded {len(df)} rows from {uploaded.name}. Close this dialog to analyze.")
        except Exception as e:
            st.error(f"Failed to load: {e}")
    if st.button("Close", key="upload_dialog_close"):
        st.rerun()


@st.dialog("Get more!", width="large")
def show_get_more_dialog():
    """Dialog with project story, open source info, GitHub and LinkedIn links."""
    st.markdown("""
I'll be honest — this was an overnight, high-enthusiasm, curiosity-driven pet project. I'm not sure I'll have the same level of energy to keep building on it. When you look at it, you might be full of ideas: login to save scenarios per account, live data, APIs for fetching prices… they all crossed my mind. But in the end, it was just a passion project led by curiosity. I have no intent to turn it into a polished product, monetize it, or derive satisfaction from perfecting it.

**But if you want to do that, you're more than welcome to!** I've made this open source. You can download it and run it yourself. It includes full documentation, so your vibe coding tool (Cursor, Copilot, etc.) can easily understand and pick it up.

**[View on GitHub](%s)**

---

If you want to discuss ideas, or just catch up and connect, you can find me on [LinkedIn](%s).
""" % (GITHUB_REPO_URL, LINKEDIN_URL))
    if st.button("Close", key="get_more_close"):
        st.session_state.pop("_open_get_more", None)
        st.rerun()


st.title("Market Simulator")
st.markdown("Compare three investment strategies with fair monthly cash inflow and liquid fund yield.")

# --- Understand me & Have suggestions buttons ---
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn1:
    understand_clicked = st.button("**Understand me**", type="primary", use_container_width=True)
with col_btn2:
    get_more_clicked = st.button("**Have suggestions, want more?**", use_container_width=True, key="get_more_btn")
if understand_clicked:
    show_understand_dialog()
if get_more_clicked:
    show_get_more_dialog()

# Apply pending snapshot BEFORE any sidebar widgets (Streamlit forbids modifying widget keys after instantiation)
if "_pending_snapshot" in st.session_state:
    snap = st.session_state.pop("_pending_snapshot")
    labels = [label for label, _ in discover_csv_files()]
    ok, err = apply_snapshot(snap, labels, None, None)
    if ok:
        st.rerun()
    else:
        st.session_state["_snapshot_error"] = err

# Sidebar inputs
with st.sidebar:
    st.header("Inputs")

    # Inject CSS for colored section backgrounds (SIP=blue, Genie=orange, Tactician=green)
    st.markdown("""
    <style>
    div[data-testid="stSidebar"] .global-section {
        border-left: 4px solid #1f77b4;
        padding-left: 0.5rem;
        margin-bottom: 0.5rem;
    }
    div[data-testid="stSidebar"] .genie-section {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%) !important;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #ff7f0e;
        margin: 0.5rem 0;
    }
    div[data-testid="stSidebar"] .tactician-section {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%) !important;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #2ca02c;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- GLOBAL SECTION (top) ---
    st.markdown('<div class="global-section"><strong>🔵 Global</strong> (SIP, Genie, Tactician)</div>', unsafe_allow_html=True)

    # Data source: uploaded or built-in
    use_uploaded = st.session_state.get("_use_uploaded_data") and "_uploaded_df" in st.session_state

    if use_uploaded:
        st.caption(f"✓ Using uploaded: **{st.session_state.get('_uploaded_filename', 'file')}**")
        if st.button("✕ Use built-in data", key="clear_upload_btn"):
            st.session_state.pop("_uploaded_df", None)
            st.session_state.pop("_uploaded_filename", None)
            st.session_state.pop("_use_uploaded_data", None)
            st.session_state.pop("_last_data_file", None)
            st.rerun()
        df_full = st.session_state["_uploaded_df"].copy()
        data_source_label = st.session_state.get("_uploaded_filename", "Uploaded")
        selected_path = None  # unused when uploaded
    else:
        csv_files = discover_csv_files()
        if not csv_files:
            st.error("No CSV files found in resources folder. Add files under resources/")
            st.stop()
        labels = [label for label, _ in csv_files]
        data_file_default = st.session_state.get("data_file", labels[0])
        data_file_idx = labels.index(data_file_default) if data_file_default in labels else 0
        selected_label = st.selectbox(
            "Data File",
            labels,
            index=data_file_idx,
            key="data_file",
            help=INFO["data_file"]
        )
        if st.button("📤 Upload my data", key="upload_my_data_btn"):
            show_upload_data_dialog()
        selected_path = next(p for l, p in csv_files if l == selected_label)
        try:
            df_full = load_price_data(selected_path)
            data_source_label = selected_label
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            st.stop()

    date_min = df_full.index.min()
    date_max = df_full.index.max()
    date_min_d = date_min.date() if hasattr(date_min, "date") else date_min
    date_max_d = date_max.date() if hasattr(date_max, "date") else date_max

    # When file changes: reset all inputs and set start/end to first and last row of CSV
    if st.session_state.get("_last_data_file") != data_source_label:
        for key in ("start_dt", "end_dt", "monthly_contribution", "liquid_fund_yield", "initial_capital",
                    "genie_val", "genie_unit", "staggered_drop_from", "staggered", "_staggered_restored"):
            st.session_state.pop(key, None)
        st.session_state["start_dt"] = date_min_d
        st.session_state["end_dt"] = date_max_d
        st.session_state["_last_data_file"] = data_source_label

    # Clamp dates to file's range (safety for snapshot restore, etc.)
    start_val = st.session_state.get("start_dt", date_min_d)
    end_val = st.session_state.get("end_dt", date_max_d)
    if start_val < date_min_d or start_val > date_max_d:
        start_val = date_min_d
        st.session_state["start_dt"] = start_val
    if end_val < date_min_d or end_val > date_max_d:
        end_val = date_max_d
        st.session_state["end_dt"] = end_val
    if end_val < start_val:
        end_val = start_val
        st.session_state["end_dt"] = end_val

    # Ensure session state is initialized for date inputs
    if "start_dt" not in st.session_state:
        st.session_state["start_dt"] = date_min_d
    if "end_dt" not in st.session_state:
        st.session_state["end_dt"] = date_max_d

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input(
            "Simulation Start",
            min_value=date_min_d,
            max_value=date_max_d,
            key="start_dt",
            help=INFO["simulation_dates"],
        )
    with col_d2:
        end_date = st.date_input(
            "Simulation End",
            min_value=start_date,
            max_value=date_max_d,
            key="end_dt",
        )
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    monthly_contribution = st.number_input(
        "Monthly Contribution (₹)", 0.0, 1e9,
        value=float(st.session_state.get("monthly_contribution", 10000)),
        step=1000.0,
        key="monthly_contribution",
        help=INFO["monthly_contribution"]
    )

    liquid_fund_yield = st.number_input(
        "Liquid Fund Yield (% annual)", 0.0, 50.0,
        value=float(st.session_state.get("liquid_fund_yield", 6)),
        step=0.5,
        key="liquid_fund_yield",
        help=INFO["liquid_fund_yield"]
    )

    initial_capital = st.number_input(
        "Initial Capital (₹)", 0.0, 1e9,
        value=float(st.session_state.get("initial_capital", 0)),
        step=1000.0,
        key="initial_capital",
        help=INFO["initial_capital"]
    )

    # --- GENIE SECTION (orange) ---
    st.markdown("")
    st.markdown("""
    <div class="genie-section">
        <p style="margin:0 0 0.5rem 0; font-weight:600; color:#e65100;">🟠 The Genie</p>
    """, unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    genie_units = ["days", "weeks", "months", "years"]
    genie_unit_default = st.session_state.get("genie_unit", "months")
    genie_unit_idx = genie_units.index(genie_unit_default) if genie_unit_default in genie_units else 2
    with col_g1:
        genie_value = st.number_input(
            "Genie Window (value)", 1, 120,
            value=int(st.session_state.get("genie_val", 6)),
            step=1,
            key="genie_val",
            help=INFO["genie_window"]
        )
    with col_g2:
        genie_unit = st.selectbox("Genie Window (unit)", genie_units, index=genie_unit_idx, key="genie_unit")
    st.markdown("</div>", unsafe_allow_html=True)

    # --- TACTICIAN SECTION (green) ---
    st.markdown("""
    <div class="tactician-section">
        <p style="margin:0 0 0.5rem 0; font-weight:600; color:#1b5e20;">🟢 Staggered Tactician</p>
    """, unsafe_allow_html=True)
    drop_options = ["All-time high", "Last purchase"]
    drop_default = st.session_state.get("staggered_drop_from", "All-time high")
    drop_idx = drop_options.index(drop_default) if drop_default in drop_options else 0
    staggered_drop_from = st.radio(
        "Invest Y% when price falls X% from:",
        options=drop_options,
        index=drop_idx,
        key="staggered_drop_from",
        help=INFO["staggered_drop_from"],
    )
    default_rules = pd.DataFrame({
        "Market Drop %": [2, 5, 10],
        "Deployment %": [10, 20, 50]
    })
    # data_editor forbids session_state writes; use _staggered_restored from snapshot apply
    if "_staggered_restored" in st.session_state:
        staggered_default = st.session_state.pop("_staggered_restored")
    else:
        staggered_default = st.session_state.get("staggered", default_rules)
    if not isinstance(staggered_default, pd.DataFrame) or staggered_default.empty:
        staggered_default = default_rules
    st.caption(INFO["staggered_rules"])
    staggered_df = st.data_editor(staggered_default, num_rows="dynamic", hide_index=True, key="staggered")
    staggered_rules = [
        {"drop_pct": float(r["Market Drop %"]), "deploy_pct": float(r["Deployment %"])}
        for _, r in staggered_df.iterrows()
    ]
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Snapshot / Restore ---
    st.markdown("---")
    with st.expander("📋 Snapshot / Restore inputs"):
        snapshot_json = json.dumps(build_snapshot(
            data_source_label, start_date, end_date, monthly_contribution, liquid_fund_yield,
            initial_capital, genie_value, genie_unit, staggered_drop_from, staggered_df
        ), indent=2)
        st.text_area("Snapshot (copy or paste)", value=snapshot_json, height=120, key="snapshot_ta")
        st.download_button("Download JSON", data=snapshot_json, file_name="market_simulator_inputs.json", mime="application/json", key="snapshot_dl")
        st.markdown("**Paste JSON to restore:**")
        paste_json = st.text_area("Paste snapshot here", height=100, key="paste_ta", placeholder='{"data_file": "...", "start_date": "2017-01-01", ...}')
        apply_clicked = st.button("Apply pasted", key="apply_paste")
        st.caption("Or upload JSON file")
        uploaded = st.file_uploader("Upload", type=["json"], key="snapshot_upload", label_visibility="collapsed")
        if "_snapshot_error" in st.session_state:
            st.error(f"Failed to apply snapshot: {st.session_state.pop('_snapshot_error')}")
        if apply_clicked and paste_json.strip():
            try:
                snap = json.loads(paste_json)
                st.session_state["_pending_snapshot"] = snap
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
        if uploaded is not None:
            try:
                snap = json.load(uploaded)
                st.session_state["_pending_snapshot"] = snap
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")

    # --- Connect ---
    st.markdown("---")
    st.markdown(
        "You can check my [LinkedIn post](%s) for more context on the motivation and story behind this."
        % LINKEDIN_POST_URL
    )

# Run simulation
config = SimulatorConfig(
    initial_capital=initial_capital,
    monthly_contribution=monthly_contribution,
    liquid_fund_yield_pct=liquid_fund_yield,
    genie_window_value=genie_value,
    genie_window_unit=genie_unit,
    staggered_rules=staggered_rules,
    staggered_drop_from="last_purchase" if staggered_drop_from == "Last purchase" else "ath",
    start_date=start_ts,
    end_date=end_ts,
)

if use_uploaded:
    df = st.session_state["_uploaded_df"][
        (st.session_state["_uploaded_df"].index >= start_ts) &
        (st.session_state["_uploaded_df"].index <= end_ts)
    ].copy()
else:
    df = load_price_data(selected_path, start_ts, end_ts)

if len(df) == 0:
    st.warning("No data in selected date range. Adjust start/end dates.")
    st.stop()

results = run_simulation(df, config)

# Results section
st.header("Results")

# Toggle buy points and all-time highs
col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1:
    show_sip_buy_points = st.checkbox("SIP buy points", value=True, key="show_sip_buy")
with col_t2:
    show_genie_buy_points = st.checkbox("Genie buy points", value=True, key="show_genie_buy")
with col_t3:
    show_staggered_buy_points = st.checkbox("Staggered buy points", value=True, key="show_staggered_buy")
with col_t4:
    show_staggered_reversal_points = st.checkbox("All-time highs", value=True, key="show_staggered_rev")

# Growth chart with deployment dots
chart_data = []
for name, res in results.items():
    for d, v in zip(res.dates, res.portfolio_values):
        chart_data.append({"Date": d, "Portfolio Value": v, "Strategy": name})

if chart_data:
    chart_df = pd.DataFrame(chart_data)
    fig = go.Figure()
    for name in chart_df["Strategy"].unique():
        sub = chart_df[chart_df["Strategy"] == name]
        fig.add_trace(go.Scatter(
            x=sub["Date"], y=sub["Portfolio Value"],
            mode="lines", name=name,
            line=dict(color=STRATEGY_COLORS.get(name, "#888"), width=2),
            legendgroup=name,
        ))

    # Close price line (secondary y-axis, right)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"].values,
        mode="lines",
        name="Close Price",
        line=dict(color="#9e9e9e", width=1.5, dash="dot"),
        yaxis="y2",
    ))

    def _close_at(d):
        """Get Close price at date d from price df."""
        ts = pd.Timestamp(d)
        if ts in df.index:
            return float(df.loc[ts, "Close"])
        idx = df.index.get_indexer([ts], method="nearest")[0]
        return float(df.iloc[idx]["Close"]) if idx >= 0 else None

    # Deployment dots on price line (y2) for visibility
    if show_sip_buy_points:
        sip_res = results.get("SIP")
        if sip_res and getattr(sip_res, "deployments", None) and sip_res.deployments:
            for dep in sip_res.deployments:
                price = _close_at(dep["date"])
                if price is None:
                    continue
                ht = f"<span style='color:{SIP_HOVER_COLOR};'><b>SIP</b><br>Amount Invested: ₹{dep['amount_deployed']:,.2f}<br>Price: ₹{price:,.2f}</span>"
                fig.add_trace(go.Scatter(
                    x=[dep["date"]], y=[price],
                    mode="markers",
                    marker=dict(symbol="circle", size=10, color=STRATEGY_COLORS["SIP"], line=dict(width=1, color="white")),
                    name="SIP deployment",
                    showlegend=False,
                    legendgroup="SIP",
                    hovertext=ht,
                    hoverinfo="text",
                    yaxis="y2",
                ))

    if show_genie_buy_points:
        genie_res = results.get("The Genie")
        if genie_res and getattr(genie_res, "deployments", None) and genie_res.deployments:
            for dep in genie_res.deployments:
                price = _close_at(dep["date"])
                if price is None:
                    continue
                ht = f"<span style='color:{GENIE_HOVER_COLOR};'><b>Genie</b><br>Amount Invested: ₹{dep['amount_deployed']:,.2f}<br>Price: ₹{price:,.2f}</span>"
                fig.add_trace(go.Scatter(
                    x=[dep["date"]], y=[price],
                    mode="markers",
                    marker=dict(symbol="circle", size=10, color=STRATEGY_COLORS["The Genie"], line=dict(width=1, color="white")),
                    name="Genie deployment",
                    showlegend=False,
                    legendgroup="The Genie",
                    hovertext=ht,
                    hoverinfo="text",
                    yaxis="y2",
                ))

    if show_staggered_buy_points:
        stag_res = results.get("Staggered Tactician")
        if stag_res and getattr(stag_res, "deployments", None) and stag_res.deployments:
            for dep in stag_res.deployments:
                price = _close_at(dep["date"])
                if price is None:
                    continue
                drop_rev = dep.get("drop_from_reversal_pct", 0)
                no_cash = dep.get("no_cash_left", False) or dep.get("total_cash_before", 0) < 1
                if no_cash:
                    ht = (
                        f"<span style='color:#d32f2f;'><b>Staggered Tactician</b></span><br>"
                        f"<span style='color:#d32f2f;'><b>Drop from all-time high:</b> {drop_rev:.2f}%</span><br>"
                        f"<span style='color:#d32f2f;'><b>No cash left</b></span><br>"
                        f"<span style='color:#d32f2f;'>Price: ₹{price:,.2f}</span>"
                    )
                    marker_cfg = dict(symbol="x", size=12, color="#d32f2f", line=dict(width=2, color="#d32f2f"))
                else:
                    ht = (
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'><b>Staggered Tactician</b></span><br>"
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'><b>Drop from all-time high:</b> {drop_rev:.2f}%</span><br>"
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'>Total Cash: ₹{dep['total_cash_before']:,.2f}</span><br>"
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'>% of remaining cash deployed: {dep['deploy_pct']:.1f}%</span><br>"
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'>Amount Deployed: ₹{dep['amount_deployed']:,.2f}</span><br>"
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'>Amount Remaining: ₹{dep['amount_remaining']:,.2f}</span><br>"
                        f"<span style='color:{STAGGERED_HOVER_COLOR};'>Price: ₹{price:,.2f}</span>"
                    )
                    marker_cfg = dict(symbol="circle", size=10, color=STRATEGY_COLORS["Staggered Tactician"], line=dict(width=1, color="white"))
                fig.add_trace(go.Scatter(
                    x=[dep["date"]], y=[price],
                    mode="markers",
                    marker=marker_cfg,
                    name="Staggered deployment",
                    showlegend=False,
                    legendgroup="Staggered Tactician",
                    hovertext=ht,
                    hoverinfo="text",
                    yaxis="y2",
                ))

    # All-time highs (on price line, right axis)
    if show_staggered_reversal_points:
        stag_res = results.get("Staggered Tactician")
        if stag_res and getattr(stag_res, "reversal_points", None) and stag_res.reversal_points:
            rev_dates = [rp[0] for rp in stag_res.reversal_points]
            rev_prices = [rp[1] for rp in stag_res.reversal_points]
            fig.add_trace(go.Scatter(
                x=rev_dates,
                y=rev_prices,
                mode="markers",
                name="All-time highs",
                marker=dict(symbol="triangle-up", size=12, color="#2ca02c", line=dict(width=1, color="white")),
                yaxis="y2",
                legendgroup="Staggered Tactician",
                hovertext=[f"All-time High: {p:,.2f}" for p in rev_prices],
                hoverinfo="text",
            ))

    fig.update_layout(
        title="Comparative Growth Chart",
        xaxis_title="Date",
        yaxis_title="Portfolio Value (₹)",
        yaxis=dict(side="left", title="Portfolio Value (₹)"),
        yaxis2=dict(
            side="right",
            title="Close Price",
            overlaying="y",
            showgrid=False,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

# Metrics table
st.subheader("Performance Metrics")
metrics_rows = []
for name, res in results.items():
    metrics_rows.append({
        "Strategy": name,
        "Total Invested (₹)": f"{res.total_invested:,.2f}",
        "Final Value (₹)": f"{res.final_value:,.2f}",
        "XIRR (%)": f"{res.xirr_pct:.2f}",
        "Max Drawdown (%)": f"{res.max_drawdown_pct:.2f}",
        "Cash Balance (₹)": f"{res.final_cash:,.2f}",
    })
metrics_df = pd.DataFrame(metrics_rows)
st.dataframe(metrics_df, use_container_width=True, hide_index=True)
