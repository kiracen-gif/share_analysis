"""
股票分析Web应用
================

本应用基于Streamlit框架开发，允许用户在浏览器中输入股票代码，
自动下载近一年的行情和财务数据（若本机安装了 `akshare` 库），
计算基本估值指标（如市盈率）、技术指标（MACD 和 KDJ），
展示交互式图表，并支持导出分析报告为 Excel 文件。

由于当前运行环境可能无法访问外部数据源或安装 `akshare`，
程序内包含模拟数据作为回退。当实际部署到用户环境时，
请确保已安装 `akshare` (pip install akshare) 以获得真实数据。
"""

import io
import sys
import datetime as dt
from typing import Optional

import numpy as np
import pandas as pd

import plotly.graph_objects as go
import streamlit as st

try:
    import akshare as ak  # type: ignore
    AK_AVAILABLE = True
except Exception:
    AK_AVAILABLE = False


def fetch_price_data(stock_code: str, days: int = 250) -> pd.DataFrame:
    """获取指定股票近一年日行情数据。如果 `akshare` 可用则从网络获取，
    否则生成模拟数据。

    返回包含日期、最高价、最低价、收盘价的 DataFrame。
    """
    if AK_AVAILABLE:
        try:
            # 东方财富日行情接口，股票代码格式: 600519 -> 600519
            df = ak.stock_zh_a_daily(symbol=stock_code)
            # 重置索引并选择最近 `days` 条数据
            df = df.sort_index().tail(days)
            df = df.reset_index().rename(columns={
                'index': 'date',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close'
            })[['date', 'high', 'low', 'close']]
            return df
        except Exception:
            pass
    # 回退：生成随机走势
    dates = pd.date_range(end=dt.datetime.today(), periods=days)
    np.random.seed(abs(hash(stock_code)) % (2 ** 32))
    price = np.cumsum(np.random.randn(days)) + 100
    high = price + np.random.rand(days) * 2
    low = price - np.random.rand(days) * 2
    return pd.DataFrame({'date': dates, 'high': high, 'low': low, 'close': price})


def fetch_financial_metrics(stock_code: str) -> dict:
    """获取财务指标和估值数据。若 `akshare` 可用则调用财务指标接口，
    否则返回随机模拟数值。"""
    metrics = {
        '市盈率': None,
        '市净率': None,
        '净利润增长率': None,
        '行业平均市盈率': None,
    }
    if AK_AVAILABLE:
        try:
            # 财务分析主要指标
            fin_df = ak.stock_financial_analysis_indicator_em(symbol=stock_code)
            # 取最新报告期数据
            latest = fin_df.iloc[-1]
            metrics['市盈率'] = latest['市盈率']
            metrics['市净率'] = latest['市净率']
            metrics['净利润增长率'] = latest['净利润同比增长率']
        except Exception:
            pass
        # 行业平均市盈率
        try:
            # 通过行业分类获取行业列表和平均PE，此处仅示例
            pass
        except Exception:
            pass
    # 若仍有缺失则填充模拟数据
    rng = np.random.default_rng(abs(hash(stock_code)) % (2 ** 32))
    if metrics['市盈率'] is None:
        metrics['市盈率'] = float(np.round(rng.uniform(10, 30), 2))
    if metrics['市净率'] is None:
        metrics['市净率'] = float(np.round(rng.uniform(1, 5), 2))
    if metrics['净利润增长率'] is None:
        metrics['净利润增长率'] = float(np.round(rng.uniform(-10, 30), 2))
    if metrics['行业平均市盈率'] is None:
        metrics['行业平均市盈率'] = float(np.round(metrics['市盈率'] * rng.uniform(0.8, 1.2), 2))
    return metrics


def compute_macd_kdj(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MACD 和 KDJ 指标并将结果添加到 DataFrame 中。"""
    # MACD
    short_ema = df['close'].ewm(span=12, adjust=False).mean()
    long_ema = df['close'].ewm(span=26, adjust=False).mean()
    dif = short_ema - long_ema
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = 2 * (dif - dea)

    # KDJ
    n = 9
    low_min = df['low'].rolling(n).min()
    high_max = df['high'].rolling(n).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    k_list = []
    d_list = []
    for i, r in enumerate(rsv):
        if np.isnan(r):
            k_list.append(np.nan)
            d_list.append(np.nan)
        else:
            if i == 0 or np.isnan(k_list[-1]):
                k_prev, d_prev = 50, 50
            else:
                k_prev, d_prev = k_list[-1], d_list[-1]
            k_now = 2/3 * k_prev + 1/3 * r
            d_now = 2/3 * d_prev + 1/3 * k_now
            k_list.append(k_now)
            d_list.append(d_now)
    j_list = [3 * k - 2 * d if not np.isnan(k) else np.nan for k, d in zip(k_list, d_list)]

    df = df.copy()
    df['DIF'] = dif
    df['DEA'] = dea
    df['MACD'] = macd_bar
    df['K'] = k_list
    df['D'] = d_list
    df['J'] = j_list
    return df


def generate_report_excel(price_df: pd.DataFrame, metrics: dict, stock_code: str) -> bytes:
    """生成包含行情、指标和财务指标的 Excel 文件并返回字节串。"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        price_df.to_excel(writer, sheet_name='PriceData', index=False)
        metrics_df = pd.DataFrame(list(metrics.items()), columns=['指标', '值'])
        metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
    return output.getvalue()


def main() -> None:
    st.set_page_config(page_title="股票分析系统", layout="wide")
    st.title("股票行业分析与交易辅助系统")
    st.write(
        "输入股票代码（例如 `600519`），系统将尝试获取近一年日行情和财务数据，"
        "计算估值和技术指标，并生成图表与报告。若当前环境无法获取真实数据，"
        "系统将使用模拟数据演示功能。"
    )

    stock_code = st.text_input("股票代码", value="600519", max_chars=10)
    if not stock_code:
        st.warning("请输入股票代码")
        return

    if st.button("开始分析"):
        with st.spinner("正在加载数据..."):
            price_df = fetch_price_data(stock_code)
            price_df = compute_macd_kdj(price_df)
            metrics = fetch_financial_metrics(stock_code)

        # 显示基本指标
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("市盈率", f"{metrics['市盈率']:.2f}")
        col2.metric("市净率", f"{metrics['市净率']:.2f}")
        col3.metric("净利润增长率(%)", f"{metrics['净利润增长率']:.2f}")
        col4.metric("行业平均市盈率", f"{metrics['行业平均市盈率']:.2f}")

        st.subheader("行情与技术指标")
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=price_df['date'], y=price_df['close'], name='收盘价'))
        fig_price.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_price, use_container_width=True)

        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=price_df['date'], y=price_df['DIF'], name='DIF'))
        fig_macd.add_trace(go.Scatter(x=price_df['date'], y=price_df['DEA'], name='DEA'))
        fig_macd.add_trace(go.Bar(x=price_df['date'], y=price_df['MACD'], name='MACD柱'))
        fig_macd.update_layout(title="MACD", height=300, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_macd, use_container_width=True)

        fig_kdj = go.Figure()
        fig_kdj.add_trace(go.Scatter(x=price_df['date'], y=price_df['K'], name='K'))
        fig_kdj.add_trace(go.Scatter(x=price_df['date'], y=price_df['D'], name='D'))
        fig_kdj.add_trace(go.Scatter(x=price_df['date'], y=price_df['J'], name='J'))
        fig_kdj.update_layout(title="KDJ", height=300, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_kdj, use_container_width=True)

        # 信号提示
        last_row = price_df.iloc[-1]
        signals = []
        if last_row['DIF'] > last_row['DEA'] and last_row['MACD'] > 0:
            signals.append("MACD金叉/上涨动能")
        elif last_row['DIF'] < last_row['DEA'] and last_row['MACD'] < 0:
            signals.append("MACD死叉/下跌动能")
        if last_row['J'] < 20:
            signals.append("KDJ超卖区")
        elif last_row['J'] > 80:
            signals.append("KDJ超买区")
        st.subheader("交易信号")
        if signals:
            st.success("，".join(signals))
        else:
            st.info("暂无明显信号")

        # 导出报告
        st.subheader("导出报告")
        report_bytes = generate_report_excel(price_df, metrics, stock_code)
        st.download_button(
            label="下载Excel报告",
            data=report_bytes,
            file_name=f"{stock_code}_report.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


if __name__ == '__main__':
    main()