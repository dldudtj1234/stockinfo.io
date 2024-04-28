from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, send_file
from yahoo_fin.stock_info import get_income_statement
from lxml_html_clean import Cleaner
import requests 
import matplotlib.pyplot as plt
import yfinance as yf
import io
import plotly 
import plotly.graph_objs as go
import json
import locale 
import pandas as pd
import requests_html
import ftplib 
import feedparser
import datetime 

app = Flask(__name__)

def format_currency(value):
    try:
        # Convert value to float if it's not None and isn't already a float
        if value is not None and not isinstance(value, float):
            value = float(value)
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_volume(value):
    try:
        # Convert value to int if it's not None and isn't already an int
        if value is not None and not isinstance(value, int):
            value = int(value)
        return f"{value:,}"
    except (ValueError, TypeError):
        return "N/A"


def is_valid_ticker(symbol):
    # Checks if the symbol is a valid stock ticker (basic check)
    return isinstance(symbol, str) and 1 <= len(symbol) <= 5 and symbol.isupper()

@app.route('/favicon.ico')
def favicon():
    return '', 204

#By using the yf, trying to fetch the balance sheet data. 
@app.route('/balance_sheet/<ticker>', methods=['GET'])
def balance_sheet(ticker):
    try:
        balance_sheet_data = yf.Ticker(ticker).balance_sheet
        fields = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Total Equity Gross Minority Interest', 'Common Stock Equity', 'Net Debt']
        filtered_balance_sheet = balance_sheet_data.loc[fields].to_dict('index')
        return render_template('balance_sheet.html', balance_sheet=filtered_balance_sheet, symbol=ticker)
    except Exception as e:
        return str(e)

# By using the yf, trying to fetch the cash flow data   
@app.route('/cash_flow/<ticker>', methods=['GET'])
def cash_flow(ticker):
    try:
         # Fetch the cash flow data
        cash_flow_data = yf.Ticker(ticker).cash_flow
        # Render the cash flow HTML template with the fetched data
        return render_template('cash_flow.html',cash_flow_data = cash_flow_data) 
    except Exception as e:
        return str(e), 500
    
@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/topstocks', methods=['GET'])
def top_stocks():
    symbols = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'FB', 'TSLA', 'BRK-B', 'TSM', 'V', 'JNJ']
    stocks_data = []
    for symbol in symbols[:10]:  # Limit to top 10 for performance reasons
        stock = yf.Ticker(symbol)
        info = stock.info
        stocks_data.append({
            'Symbol': symbol,
            'Name': info.get('shortName'),
            'Market_Cap': format_currency(info.get('marketCap')),
            'Price': format_currency(info.get('currentPrice')),
            'Volume': format_volume(info.get('volume'))
        })
    return jsonify(stocks_data)



@app.route('/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    def get_stock_data(symbol):
    # Check if the symbol is a valid ticker
        if not is_valid_ticker(symbol):
            return jsonify({'error': 'Invalid ticker symbol'}), 400
    stock = yf.Ticker(symbol)
    info= stock.info
    # Check if important information like currentPrice is missing
    if not info or 'currentPrice' not in info or info['currentPrice'] is None:
        # Redirect to a Google search if the stock data is not available (with the symbol)
        search_url = f"https://finance.yahoo.com/quote/{symbol}"
        return redirect(search_url)
    try:
        hist = stock.history(period="1d")
        info = stock.info
        data = {
            'Previous Close': format_currency(float(hist['Close'].iloc[-1])),
            'Open': format_currency(float(hist['Open'].iloc[-1])),
            'Day\'s Range': format_currency(f"{float(hist['Low'].iloc[-1])} - {float(hist['High'].iloc[-1])}"),
            '52 Week Range': format_currency(f"{float(info['fiftyTwoWeekLow'])} - {float(info['fiftyTwoWeekHigh'])}"),
            'Volume': format_volume(float(hist['Volume'].iloc[-1])),
            'Market Cap (Intraday)': format_currency(float(info['marketCap'])),
            'Beta (5Y Monthly)': float(info.get('beta', 0))  # Use .get() to avoid KeyError if 'beta' is missing
        }

        return render_template('result.html', data=data, symbol=symbol)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/<symbol>', methods=['GET'])
def stock_graph(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1y")  # Get 1 year of stock data

    # Create a line chart
    trace = go.Scatter(
        x=hist.index,
        y=hist['Close'],
        mode='lines+markers',
        name='Close Prices',
        line=dict(color='RoyalBlue', width=2),
        marker=dict(color='LightSkyBlue', size=8, line=dict(width=2, color='DarkSlateGrey'))
    )

    layout = go.Layout(
        title=f'{symbol.upper()} Closing Prices',
        title_x=0.5,
        xaxis=dict(
            title='Date',
            titlefont=dict(size=18, color='DarkSlateGrey'),
            showline=True,
            showgrid=False,
            showticklabels=True,
            linecolor='Grey',
            linewidth=2,
            ticks='outside',
            tickfont=dict(size=12, color='DarkSlateGrey')
        ),
        yaxis=dict(
            title='Price (USD)',
            titlefont=dict(size=18, color='DarkSlateGrey'),
            showline=True,
            showgrid=True,
            showticklabels=True,
            gridcolor='LightGrey',
            linecolor='Grey',
            linewidth=2,
            ticks='outside',
            tickfont=dict(size=12, color='DarkSlateGrey')
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor='whitesmoke',
        plot_bgcolor='whiteSmoke',
        hovermode='x'
    )
    
    fig = go.Figure(data=[trace], layout=layout)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('Graph.html', graph_json=graph_json, symbol=symbol)

if __name__ == '__main__':
    app.run(debug=True)