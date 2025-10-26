#!/usr/bin/env python3
"""
Plotly Demo for BenchmarkOS Financial Dashboard
Demonstrates Plotly integration for financial data visualization
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_sample_data():
    """Create sample financial data for demonstration."""
    print("📊 Creating sample financial data...")
    
    # Generate date range
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='M')
    
    # Generate sample stock data
    np.random.seed(42)
    stock_prices = 100 + np.cumsum(np.random.randn(len(dates)) * 2)
    revenues = 1000 + np.cumsum(np.random.randn(len(dates)) * 50)
    profits = 200 + np.cumsum(np.random.randn(len(dates)) * 20)
    
    # Generate financial ratios
    pe_ratios = 15 + np.random.randn(len(dates)) * 5
    roe_values = 10 + np.random.randn(len(dates)) * 3
    
    # Create DataFrame
    df = pd.DataFrame({
        'Date': dates,
        'Stock_Price': stock_prices,
        'Revenue': revenues,
        'Profit': profits,
        'PE_Ratio': pe_ratios,
        'ROE': roe_values
    })
    
    print(f"✅ Generated {len(df)} data points")
    return df

def create_stock_price_chart(df):
    """Create interactive stock price chart."""
    print("📈 Creating stock price chart...")
    
    fig = go.Figure()
    
    # Add stock price line
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Stock_Price'],
        mode='lines+markers',
        name='Stock Price',
        line=dict(color='#667eea', width=3),
        marker=dict(size=6, color='#667eea'),
        hovertemplate='<b>Date:</b> %{x}<br><b>Price:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Stock Price Trend',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#495057'}
        },
        xaxis_title='Date',
        yaxis_title='Price ($)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif'),
        hovermode='x unified'
    )
    
    return fig

def create_revenue_profit_chart(df):
    """Create revenue vs profit comparison chart."""
    print("💰 Creating revenue vs profit chart...")
    
    fig = go.Figure()
    
    # Add revenue bars
    fig.add_trace(go.Bar(
        x=df['Date'],
        y=df['Revenue'],
        name='Revenue',
        marker_color='#28a745',
        hovertemplate='<b>Date:</b> %{x}<br><b>Revenue:</b> $%{y:.0f}M<extra></extra>'
    ))
    
    # Add profit bars
    fig.add_trace(go.Bar(
        x=df['Date'],
        y=df['Profit'],
        name='Profit',
        marker_color='#dc3545',
        hovertemplate='<b>Date:</b> %{x}<br><b>Profit:</b> $%{y:.0f}M<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Revenue vs Profit Comparison',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#495057'}
        },
        xaxis_title='Date',
        yaxis_title='Amount ($M)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif'),
        barmode='group'
    )
    
    return fig

def create_financial_ratios_chart(df):
    """Create financial ratios chart with dual y-axis."""
    print("📊 Creating financial ratios chart...")
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('P/E Ratio Trend', 'ROE Trend'),
        vertical_spacing=0.1
    )
    
    # P/E Ratio
    fig.add_trace(
        go.Scatter(
            x=df['Date'],
            y=df['PE_Ratio'],
            mode='lines+markers',
            name='P/E Ratio',
            line=dict(color='#667eea', width=3),
            marker=dict(size=6, color='#667eea')
        ),
        row=1, col=1
    )
    
    # ROE
    fig.add_trace(
        go.Scatter(
            x=df['Date'],
            y=df['ROE'],
            mode='lines+markers',
            name='ROE (%)',
            line=dict(color='#28a745', width=3),
            marker=dict(size=6, color='#28a745')
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Financial Ratios Analysis',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#495057'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif'),
        height=600
    )
    
    return fig

def create_sector_comparison_chart():
    """Create sector comparison pie chart."""
    print("🏢 Creating sector comparison chart...")
    
    # Sample sector data
    sectors = ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer']
    values = [35, 25, 20, 15, 5]
    colors = ['#667eea', '#28a745', '#dc3545', '#ffc107', '#17a2b8']
    
    fig = go.Figure(data=[go.Pie(
        labels=sectors,
        values=values,
        marker_colors=colors,
        textinfo='label+percent',
        textfont_size=12,
        hovertemplate='<b>%{label}</b><br>Value: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title={
            'text': 'Sector Distribution',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#495057'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif')
    )
    
    return fig

def create_dashboard_html(figs, output_file='plotly_dashboard.html'):
    """Create complete dashboard HTML."""
    print("🌐 Creating dashboard HTML...")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Plotly Financial Dashboard - BenchmarkOS</title>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                padding: 30px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e9ecef;
            }}
            .header h1 {{
                color: #667eea;
                margin: 0 0 10px 0;
                font-size: 2.5em;
            }}
            .chart-container {{
                margin: 30px 0;
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            }}
            .chart-title {{
                color: #495057;
                margin: 0 0 15px 0;
                font-size: 1.3em;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Plotly Financial Dashboard</h1>
                <p>Interactive financial charts powered by Plotly.js</p>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📈 Stock Price Trend</h3>
                <div id="stockChart" style="width: 100%; height: 400px;"></div>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">💰 Revenue vs Profit</h3>
                <div id="revenueChart" style="width: 100%; height: 400px;"></div>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📊 Financial Ratios</h3>
                <div id="ratiosChart" style="width: 100%; height: 600px;"></div>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">🏢 Sector Comparison</h3>
                <div id="sectorChart" style="width: 100%; height: 400px;"></div>
            </div>
        </div>
        
        <script>
            // Plotly chart data
            const stockData = {figs[0].to_json()};
            const revenueData = {figs[1].to_json()};
            const ratiosData = {figs[2].to_json()};
            const sectorData = {figs[3].to_json()};
            
            // Render charts
            Plotly.newPlot('stockChart', stockData.data, stockData.layout, {{responsive: true}});
            Plotly.newPlot('revenueChart', revenueData.data, revenueData.layout, {{responsive: true}});
            Plotly.newPlot('ratiosChart', ratiosData.data, ratiosData.layout, {{responsive: true}});
            Plotly.newPlot('sectorChart', sectorData.data, sectorData.layout, {{responsive: true}});
        </script>
    </body>
    </html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard saved to {output_file}")
    return output_file

def main():
    """Main function to create Plotly demo."""
    print("🚀 Plotly Financial Dashboard Demo")
    print("=" * 50)
    
    try:
        # Create sample data
        df = create_sample_data()
        
        # Create charts
        charts = [
            ("Stock Price", create_stock_price_chart(df)),
            ("Revenue vs Profit", create_revenue_profit_chart(df)),
            ("Financial Ratios", create_financial_ratios_chart(df)),
            ("Sector Comparison", create_sector_comparison_chart())
        ]
        
        # Save individual charts
        for name, fig in charts:
            filename = f"plotly_{name.lower().replace(' ', '_')}.html"
            fig.write_html(filename)
            print(f"✅ {name} chart saved to {filename}")
        
        # Create complete dashboard
        figs = [fig for _, fig in charts]
        dashboard_file = create_dashboard_html(figs)
        
        print("\n🎉 Plotly Demo Complete!")
        print("\n📁 Generated Files:")
        for name, _ in charts:
            filename = f"plotly_{name.lower().replace(' ', '_')}.html"
            print(f"   • {filename}")
        print(f"   • {dashboard_file}")
        
        print("\n💡 Next Steps:")
        print("1. Open dashboard in browser:")
        print(f"   open {dashboard_file}")
        print("2. Install Plotly dependencies:")
        print("   pip install plotly dash dash-bootstrap-components")
        print("3. Integrate with your application:")
        print("   import plotly.graph_objects as go")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install Plotly dependencies:")
        print("   pip install plotly dash dash-bootstrap-components")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
