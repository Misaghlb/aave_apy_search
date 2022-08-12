from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title='Aave Dashboard', layout='wide', page_icon=':dollar:')
st.title("Aave v2 and v3 Dashboard - Historical APY Search Tool")


def clean_rate(rates: list, day: datetime, asset: str):
    for rate in rates:
        rate['Day'] = day
        rate['asset'] = asset
        rate['rate'] = float(rate['rate'])
        rate['type'] = f"{rate['side']}-{rate['type']}"
    return rates


# @st.cache(ttl=24 * 60 * 60)  # 6 hours
def fetch_data(url: str, timestamp_start, timestamp_end):
    first = 1000
    block_number = 0
    raw_data = []
    rates = []
    while True:
        payload = {
            "query": """
            { marketDailySnapshots(first:%s, orderBy: blockNumber,
                  orderDirection: asc, where:{blockNumber_gt: %s, timestamp_gte: %s, timestamp_lte: %s})

                  { dailyBorrowUSD dailyLiquidateUSD 
                    dailyRepayUSD blockNumber 
                    timestamp totalValueLockedUSD 
                    dailyDepositUSD dailyWithdrawUSD
                    dailySupplySideRevenueUSD
                    dailyProtocolSideRevenueUSD
                    market { id name }
                    rates {
                      rate type side
                    }
                  } 
                } 
            """ % (
                first, block_number, timestamp_start, timestamp_end),
        }
        res = requests.post(url=url,
                            json=payload).json()
        if not res['data']['marketDailySnapshots']:
            break
        raw_data.extend(res['data']['marketDailySnapshots'])
        block_number = max([int(b['blockNumber']) for b in raw_data])

    for item in raw_data:
        item['Day'] = datetime.fromtimestamp(int(item['timestamp'])).date()
        item['Asset'] = item['market']['name']
        item['TVL'] = int(float(item['totalValueLockedUSD']))
        item['dailyDepositUSD'] = int(float(item['dailyDepositUSD']))
        item['dailyWithdrawUSD'] = int(float(item['dailyWithdrawUSD']))
        item['dailyBorrowUSD'] = int(float(item['dailyBorrowUSD']))
        item['dailyLiquidateUSD'] = int(float(item['dailyLiquidateUSD']))
        item['dailyRepayUSD'] = int(float(item['dailyRepayUSD']))

        item['dailySupplySideRevenueUSD'] = float(item['dailySupplySideRevenueUSD'])
        item['dailyProtocolSideRevenueUSD'] = float(item['dailyProtocolSideRevenueUSD'])

        cleaned_rates = clean_rate(item['rates'], item['Day'], item['Asset'])
        rates.extend(cleaned_rates)

    rates = pd.DataFrame(
        rates,
        columns=["Day", 'type', "asset", "rate"])

    return [rates, pd.DataFrame(
        raw_data,
        columns=["Day", "TVL", 'dailyDepositUSD', 'dailyWithdrawUSD', "Asset", "dailyBorrowUSD", "dailyLiquidateUSD",
                 "dailyRepayUSD", "dailySupplySideRevenueUSD", "dailyProtocolSideRevenueUSD"])
            ]


def generate_supply_charts(list_data: list):
    rates_data = list_data[0]
    chart_data = list_data[1]
    rates_data = rates_data.loc[(rates_data['rate'] <= 10) & (rates_data['rate'] > 0)]
    rates_chart_data = rates_data.groupby(["Day", "type"], as_index=False).mean()

    fig = px.line(rates_chart_data, x='Day', y='rate', color='type',
                  title="average Supply and Borrow(stable and variable) Rates over time",
                  template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    # --------------------------
    # --------------------------

    c1, c2, c3 = st.columns(3)
    # ------------ rates_stable_assets_one_month
    rates_stable_assets = rates_data[rates_data['type'] == 'BORROWER-STABLE']
    rates_stable_assets = rates_stable_assets.groupby(["asset"], as_index=False).mean()

    fig = px.bar(rates_stable_assets, x='asset', y='rate',
                 title="average Stable borrow rates in selected range",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c1.plotly_chart(fig, use_container_width=True)

    # ------------ rates_stable_assets_one_month
    rates_var_assets = rates_data[rates_data['type'] == 'BORROWER-VARIABLE']
    rates_var_assets = rates_var_assets.groupby(["asset"], as_index=False).mean()

    fig = px.bar(rates_var_assets, x='asset', y='rate',
                 title="average Variable borrow rates in selected range",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c2.plotly_chart(fig, use_container_width=True)

    # ------------ rates_stable_assets_one_month
    rates_supply_assets = rates_data[rates_data['type'] == 'LENDER-VARIABLE']
    rates_supply_assets = rates_supply_assets.groupby(["asset"], as_index=False).mean()

    fig = px.bar(rates_supply_assets, x='asset', y='rate', title="average supply rates in selected range",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c3.plotly_chart(fig, use_container_width=True)
    # -------------------------------------------------------------------------

    fig = px.bar(chart_data, x='Day', y='dailySupplySideRevenueUSD', color='Asset',
                 title="daily Supply Side Revenue in USD",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    # -------------------------------------------------------------------------

    fig = px.bar(chart_data, x='Day', y='dailyProtocolSideRevenueUSD', color='Asset',
                 title="daily Protocol Side Revenue in USD",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    # -------------------------------------------------------------------------


with st.spinner('Updating Dashboard...'):
    with st.form("my_form"):

        activation_function = st.selectbox('Choose a Chain',
                                           ['Avalanche v2', 'Avalanche v3', 'Ethereum', 'Optimism', 'Fantom',
                                            'Arbitrum',
                                            'Harmony', 'Polygon v2', 'Polygon v3'])
        start_time = st.slider(
            "When do you start?",
            value=datetime.now() - timedelta(days=30), min_value=datetime(2019, 1, 1), max_value=datetime.now(),
            format="yy/MM/DD")
        start_timestamp = int(start_time.timestamp())

        end_time = st.slider(
            "When do you End?",
            value=datetime.now(), min_value=datetime(2019, 1, 1), max_value=datetime.now(),
            format="yy/MM/DD")
        end_timestamp = int(end_time.timestamp())

        submitted = st.form_submit_button("Submit")

        if submitted:

            if activation_function == 'Avalanche v2':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v2-avalanche-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Avalanche v3':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v3-avalanche',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Ethereum':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v2-ethereum-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Optimism':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v3-optimism-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Polygon v3':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v3-polygon-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Polygon v2':
                st.warning('The database is in the process of updating and has not been fully backfilled')
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v2-polygon-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Harmony':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v3-harmony-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Fantom':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v3-fantom-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)

            if activation_function == 'Arbitrum':
                chart_data = fetch_data('https://api.thegraph.com/subgraphs/name/messari/aave-v3-arbitrum-extended',
                                        start_timestamp, end_timestamp)
                generate_supply_charts(chart_data)
