import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(
    page_title="Demand Zone Scanner",
    page_icon="📈",
    layout="wide"
)

# ── DB connection ───────────────────────────────────────────
@st.cache_resource
def get_conn():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def run_query(as_of_date: date, market: str) -> pd.DataFrame:
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM find_demand_zones(%s, %s)",
            (as_of_date, market)
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Sidebar controls ────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Controls")

    as_of = st.date_input(
        "As of date",
        value=date.today(),
        help="Evaluate zones as of this date (historical replay supported)"
    )

    market = st.selectbox(
        "Market",
        options=["US", "IN", "ALL"],
        index=0,
        help="US = NYSE/NASDAQ · IN = NSE (.NS) · ALL = both"
    )

    grades = st.multiselect(
        "Zone grade",
        options=["A", "B", "C"],
        default=["A", "B"],
    )

    status_filter = st.multiselect(
        "Price vs zone",
        options=["above_zone", "inside_zone"],
        default=["above_zone", "inside_zone"],
    )

    max_pct_above = st.slider(
        "Max % above zone top",
        min_value=0, max_value=200, value=100, step=5,
        help="Filter out stocks too far above the zone"
    )

    run = st.button("🔍 Scan", use_container_width=True, type="primary")

# ── Main ────────────────────────────────────────────────────
st.title("📈 Demand Zone Scanner")
st.caption(f"Weekly candles · 2-year lookback · base-before-impulse method")

if run or "df" not in st.session_state:
    with st.spinner("Running scanner..."):
        try:
            df = run_query(as_of, market)
            st.session_state["df"] = df
            st.session_state["params"] = (as_of, market)
        except Exception as e:
            st.error(f"Query failed: {e}")
            st.stop()

df = st.session_state.get("df", pd.DataFrame())

if df.empty:
    st.info("No demand zones found for the selected filters.")
    st.stop()

# Apply sidebar filters
df = df[df["zone_grade"].isin(grades)]
df = df[df["price_vs_zone"].isin(status_filter)]
df = df[df["pct_above_zone"] <= max_pct_above]

if df.empty:
    st.warning("No zones match the current filters — try loosening them.")
    st.stop()

# ── Summary metrics ─────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Zones found", len(df))
col2.metric("Grade A", len(df[df["zone_grade"] == "A"]))
col3.metric("Inside zone", len(df[df["price_vs_zone"] == "inside_zone"]))
col4.metric("Avg % above zone", f"{df['pct_above_zone'].mean():.1f}%")
col5.metric("Closest to zone", df.loc[df["pct_above_zone"].idxmin(), "symbol"])

st.divider()

# ── Data table ──────────────────────────────────────────────
st.subheader("All zones")

display_cols = [
    "symbol", "market", "zone_grade", "current_price",
    "zone_top", "zone_bottom", "invalidation_level",
    "price_vs_zone", "pct_above_zone", "pct_rally_from_zone",
    "times_tested", "consolidation_weeks",
    "base_start", "impulse_week"
]

def color_grade(val):
    colors = {"A": "background-color:#EAF3DE;color:#27500A",
              "B": "background-color:#FAEEDA;color:#633806",
              "C": "background-color:#FAECE7;color:#4A1B0C"}
    return colors.get(val, "")

def color_status(val):
    if val == "inside_zone":
        return "background-color:#E6F1FB;color:#0C447C"
    return ""

styled = (
    df[display_cols]
    .style
    .applymap(color_grade, subset=["zone_grade"])
    .applymap(color_status, subset=["price_vs_zone"])
    .format({
        "current_price": "${:.2f}",
        "zone_top": "${:.2f}",
        "zone_bottom": "${:.2f}",
        "invalidation_level": "${:.2f}",
        "pct_above_zone": "{:.1f}%",
        "pct_rally_from_zone": "+{:.1f}%",
    })
)
st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ── Charts ──────────────────────────────────────────────────
st.subheader("Price vs demand zone")

# Sort by proximity for chart
df_sorted = df.sort_values("pct_above_zone")

fig = go.Figure()

# Demand zone band
fig.add_trace(go.Bar(
    name="Demand zone",
    x=df_sorted["symbol"],
    y=df_sorted["zone_top"] - df_sorted["zone_bottom"],
    base=df_sorted["zone_bottom"],
    marker_color="rgba(29,158,117,0.25)",
    marker_line_color="#1D9E75",
    marker_line_width=1.5,
    hovertemplate="<b>%{x}</b><br>Zone: $%{base:.2f} – $%{y:.2f}<extra></extra>",
))

# Current price marker
fig.add_trace(go.Scatter(
    name="Current price",
    x=df_sorted["symbol"],
    y=df_sorted["current_price"],
    mode="markers",
    marker=dict(symbol="diamond", size=12, color="#534AB7",
                line=dict(color="#fff", width=1.5)),
    hovertemplate="<b>%{x}</b><br>Current: $%{y:.2f}<extra></extra>",
))

# Invalidation level
fig.add_trace(go.Scatter(
    name="Invalidation",
    x=df_sorted["symbol"],
    y=df_sorted["invalidation_level"],
    mode="markers",
    marker=dict(symbol="line-ew", size=14, color="#D85A30",
                line=dict(color="#D85A30", width=2)),
    hovertemplate="<b>%{x}</b><br>Invalidation: $%{y:.2f}<extra></extra>",
))

fig.update_layout(
    height=380,
    margin=dict(l=0, r=0, t=10, b=0),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(title="Price ($)", gridcolor="rgba(128,128,128,0.1)"),
    xaxis=dict(title=""),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    barmode="overlay",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Per-symbol detail cards ──────────────────────────────────
st.subheader("Zone detail")

cols_per_row = 2
symbols = df_sorted["symbol"].tolist()
for i in range(0, len(symbols), cols_per_row):
    row_syms = symbols[i:i+cols_per_row]
    cols = st.columns(cols_per_row)
    for col, sym in zip(cols, row_syms):
        r = df_sorted[df_sorted["symbol"] == sym].iloc[0]
        with col:
            with st.container(border=True):
                g_color = {"A":"🟢","B":"🟡","C":"🟠"}.get(r["zone_grade"],"⚪")
                st.markdown(f"### {g_color} {sym} &nbsp; `Grade {r['zone_grade']}`")

                m1, m2, m3 = st.columns(3)
                m1.metric("Current", f"${r['current_price']:.2f}")
                m2.metric("Zone top", f"${r['zone_top']:.2f}")
                m3.metric("Zone bottom", f"${r['zone_bottom']:.2f}")

                # Mini sparkline: zone bottom → zone top → current
                mini = go.Figure()
                mini.add_shape(type="rect",
                    x0=0, x1=1, y0=r["zone_bottom"], y1=r["zone_top"],
                    fillcolor="rgba(29,158,117,0.15)",
                    line=dict(color="#1D9E75", width=1))
                mini.add_shape(type="line",
                    x0=0, x1=1, y0=r["invalidation_level"], y1=r["invalidation_level"],
                    line=dict(color="#D85A30", width=1, dash="dot"))
                mini.add_trace(go.Scatter(
                    x=[0.5], y=[r["current_price"]],
                    mode="markers",
                    marker=dict(size=14, color="#534AB7", symbol="diamond"),
                    showlegend=False,
                    hovertemplate=f"Current: ${r['current_price']:.2f}<extra></extra>"
                ))
                mini.update_layout(
                    height=130, margin=dict(l=0,r=0,t=4,b=0),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(visible=False),
                    yaxis=dict(gridcolor="rgba(128,128,128,0.1)", tickprefix="$"),
                )
                st.plotly_chart(mini, use_container_width=True)

                st.markdown(f"""
| | |
|---|---|
| % above zone | `{r['pct_above_zone']:.1f}%` |
| Rally from zone | `+{r['pct_rally_from_zone']:.1f}%` |
| Times tested | `{r['times_tested']}` |
| Consolidation | `{r['consolidation_weeks']} weeks` |
| Base | `{r['base_start']}` → `{r['base_end']}` |
| Impulse week | `{r['impulse_week']}` |
| Invalidation | `${r['invalidation_level']:.2f}` |
""")
