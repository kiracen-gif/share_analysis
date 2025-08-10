# app.py
import io, base64, datetime as dt
import pandas as pd
import numpy as np
import streamlit as st
from app.utils import fetch_price_df, fetch_financials, macd, kdj

st.set_page_config(page_title="Stock Insight", page_icon="📈", layout="wide")

# --- Minimal clean UI ---
st.markdown("""
<style>
/* cards */
.block-container {padding-top: 1.2rem;}
.card {border-radius: 14px; padding: 16px; background: var(--secondary-background-color); border: 1px solid rgba(255,255,255,0.06);}
.metric {font-size: 28px; font-weight: 700; margin-bottom: 4px;}
.metric-sub {opacity: .8; font-size: 13px;}
hr {border: none; border-top: 1px solid rgba(255,255,255,.08); margin: 8px 0 16px;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("📈 Stock Insight")
    code = st.text_input("输入股票代码 / Ticker", value="600519")  # Kweichow Moutai as example
    years = st.slider("历史区间（年）", 1, 5, 1)
    st.caption("Tip：A股可填6位数（自动判定沪/深）；美股/港股可直接填 Ticker。")
    run = st.button("运行分析")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["概览", "估值/财务", "技术面", "新闻/行业", "导出报告"])

if run and code:
    end = dt.date.today()
    start = end - dt.timedelta(days=365*years)
    with st.spinner("抓取行情与财务数据…"):
        px = fetch_price_df(code, start, end)
        fin = fetch_financials(code)

    # === 概览 ===
    with tab1:
        st.subheader("价格走势")
        st.line_chart(px["close"])

        # metrics
        chg_1m = (px["close"].iloc[-1]/px["close"].iloc[-21]-1)*100 if len(px)>21 else np.nan
        chg_3m = (px["close"].iloc[-1]/px["close"].iloc[-63]-1)*100 if len(px)>63 else np.nan
        chg_1y = (px["close"].iloc[-1]/px["close"].iloc[0]-1)*100 if len(px)>1 else np.nan

        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="card"><div class="metric">{px["close"].iloc[-1]:.2f}</div><div class="metric-sub">最新收盘</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="metric">{chg_3m:.1f}%</div><div class="metric-sub">近3个月</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="card"><div class="metric">{chg_1y:.1f}%</div><div class="metric-sub">近1年</div></div>', unsafe_allow_html=True)

    # === 估值/财务 ===
    with tab2:
        st.subheader("关键指标（若抓取失败则为空）")
        cols = st.columns(4)
        keys = ["市盈率TTM","市净率","ROE加权","扣非净利润同比增长率"]
        vals = [fin.get(k) for k in keys]
        labels = ["PE (TTM)","PB","ROE(加权)","扣非净利YoY"]
        for col, lab, v in zip(cols, labels, vals):
            val = "—" if v is None else f"{v}"
            col.markdown(f'<div class="card"><div class="metric">{val}</div><div class="metric-sub">{lab}</div></div>', unsafe_allow_html=True)

    # === 技术面 ===
    with tab3:
        st.subheader("MACD / KDJ")
        ind_macd = macd(px["close"])
        ind_kdj = kdj(px["high"], px["low"], px["close"])
        st.line_chart(ind_macd)
        st.line_chart(ind_kdj)

    # === 新闻/行业（占位，按需接入） ===
    with tab4:
        st.subheader("新闻与行业情绪（占位）")
        st.write("为避免云端限流，此处建议接入你可控的数据源或缓存层。")

    # === 导出报告 ===
    with tab5:
        st.subheader("导出 Excel 报告")
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            px.tail(250).to_excel(writer, sheet_name="Price", index=True)
            pd.DataFrame({"指标":["PE_TTM","PB","ROE","扣非净利YoY"],
                          "值":[fin.get("市盈率TTM"), fin.get("市净率"), fin.get("ROE加权"), fin.get("扣非净利润同比增长率")]}).to_excel(writer, sheet_name="Valuation", index=False)
            macd(px["close"]).to_excel(writer, sheet_name="MACD", index=True)
            kdj(px["high"], px["low"], px["close"]).to_excel(writer, sheet_name="KDJ", index=True)
        st.download_button("下载 Excel 报告", data=buf.getvalue(), file_name=f"{code}_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    with tab1:
        st.info("在左侧输入股票代码并点击【运行分析】。")
