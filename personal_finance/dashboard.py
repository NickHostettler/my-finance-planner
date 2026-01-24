"""
Dash Dashboard Application

Interaktives Dashboard für Finanzanalyse und Szenario-Vergleich.
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List
import json

from personal_finance.calculator import FinanceCalculator


# Initialize Dash App
app = dash.Dash(__name__)
app.title = "Swiss Personal Finance Planner"

# Define color scheme
colors = {
    'background': '#f8f9fa',
    'text': '#2c3e50',
    'primary': '#3498db',
    'success': '#27ae60',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'light': '#ecf0f1',
}

# App layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🇨🇭 Swiss Personal Finance Planner", className="mb-4"),
        html.P("Analyse der Altersvorsorge: 2. Säule, 3a Szenarien, und private Sparziele"),
    ], className="container-fluid p-4", style={'backgroundColor': colors['primary'], 'color': 'white'}),
    
    # Main container
    html.Div([
        # Input Section
        html.Div([
            html.H3("📋 Eingaben", className="mb-3"),
            html.Div([
                html.Div([
                    html.Label("Monatliches Nettoeinkommen (CHF):"),
                    dcc.Input(
                        id='monthly-income-input',
                        type='number',
                        placeholder='z.B. 5000',
                        value=5000,
                        min=0,
                        step=100,
                        className="form-control",
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                    ),
                ], className="col-md-4"),
                
                html.Div([
                    html.Label("Aktuelles Alter:"),
                    dcc.Input(
                        id='current-age-input',
                        type='number',
                        placeholder='z.B. 35',
                        value=35,
                        min=15,
                        max=100,
                        step=1,
                        className="form-control",
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                    ),
                ], className="col-md-4"),
                
                html.Div([
                    html.Label("Pensionierungsalter:"),
                    dcc.Input(
                        id='retirement-age-input',
                        type='number',
                        placeholder='z.B. 65',
                        value=65,
                        min=55,
                        max=75,
                        step=1,
                        className="form-control",
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                    ),
                ], className="col-md-4"),
            ], className="row"),
            
            html.Div([
                html.Div([
                    html.Label("3a Sparquote (%):"),
                    dcc.Slider(
                        id='pillar3a-rate-slider',
                        min=0,
                        max=20,
                        step=1,
                        value=10,
                        marks={i: f'{i}%' for i in range(0, 21, 5)},
                        className="slider",
                    ),
                    html.Div(id='slider-output-container', style={'marginTop': '10px'}),
                ], className="col-md-6"),
                
                html.Div([
                    html.Label("oder monatlicher Betrag (CHF):"),
                    dcc.Input(
                        id='pillar3a-amount-input',
                        type='number',
                        placeholder='Leer für Sparquote verwenden',
                        min=0,
                        step=100,
                        className="form-control",
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                    ),
                ], className="col-md-6"),
            ], className="row"),
            
            html.Button(
                '📊 Berechnen',
                id='calculate-button',
                n_clicks=0,
                className="btn btn-primary",
                style={'width': '100%', 'marginTop': '20px', 'padding': '10px', 'fontSize': '16px'}
            ),
        ], className="card p-4 mb-4", style={'backgroundColor': colors['light']}),
        
        # Results Section
        html.Div(id='results-section', children=[]),
        
    ], className="container mt-4 mb-4"),
    
    # Store for calculations
    dcc.Store(id='calculation-store'),
    
], style={'backgroundColor': colors['background'], 'minHeight': '100vh'})


# Callbacks
@app.callback(
    Output('slider-output-container', 'children'),
    Input('pillar3a-rate-slider', 'value')
)
def update_slider_output(value):
    return f"Ausgewählte Sparquote: {value}%"


@app.callback(
    Output('calculation-store', 'data'),
    Input('calculate-button', 'n_clicks'),
    [
        State('monthly-income-input', 'value'),
        State('current-age-input', 'value'),
        State('retirement-age-input', 'value'),
        State('pillar3a-rate-slider', 'value'),
        State('pillar3a-amount-input', 'value'),
    ],
    prevent_initial_call=True
)
def perform_calculation(n_clicks, income, current_age, retirement_age, rate, amount):
    try:
        if not income or current_age is None or retirement_age is None:
            return None
        
        calculator = FinanceCalculator(
            monthly_net_income=float(income),
            current_age=int(current_age),
            retirement_age=int(retirement_age),
        )
        
        # Always run complete analysis with savings rate (amount is optional override)
        rate_decimal = float(rate) / 100 if rate else 0.10
        analysis = calculator.complete_analysis(pillar3a_savings_rate=rate_decimal)
        
        # Convert to JSON-serializable format
        result = {
            'monthly_income': float(income),
            'current_age': int(current_age),
            'retirement_age': int(retirement_age),
            'years_to_retirement': analysis.years_to_retirement,
            'pillar2': {
                'monthly_total': float(analysis.pillar2.annual_contribution_total / 12),
                'monthly_employee': float(analysis.pillar2.annual_contribution_employee / 12),
                'monthly_employer': float(analysis.pillar2.annual_contribution_employer / 12),
                'estimated_capital': float(analysis.pillar2.estimated_capital_at_retirement),
            },
            'pillar3a_scenarios': {
                name: {
                    'monthly': float(scenario.monthly_savings),
                    'annual': float(scenario.annual_savings),
                    'total_at_retirement': float(scenario.total_at_retirement),
                    'contributions': float(scenario.total_contributions),
                    'gains': float(scenario.investment_gains),
                    'yearly_breakdown': [
                        {
                            'year': y['year'],
                            'age': y['age'],
                            'contribution': float(y['annual_contribution']),
                            'interest': float(y['interest_earned']),
                            'balance': float(y['year_end_balance']),
                        }
                        for y in scenario.yearly_breakdown
                    ]
                }
                for name, scenario in analysis.pillar3a_scenarios.items()
            },
            'pillar3b_scenarios': {
                name: {
                    'monthly': float(scenario.monthly_savings),
                    'annual': float(scenario.annual_savings),
                    'total_at_retirement': float(scenario.total_at_retirement),
                    'contributions': float(scenario.total_contributions),
                    'gains': float(scenario.investment_gains),
                    'yearly_breakdown': [
                        {
                            'year': y['year'],
                            'age': y['age'],
                            'contribution': float(y['annual_contribution']),
                            'interest': float(y['interest_earned']),
                            'balance': float(y['year_end_balance']),
                        }
                        for y in scenario.yearly_breakdown
                    ]
                }
                for name, scenario in analysis.pillar3b_scenarios.items()
            },
            'summary': analysis.summary,
        }
        
        return result
    
    except Exception as e:
        print(f"Calculation error: {str(e)}")
        return None


@app.callback(
    Output('results-section', 'children'),
    Input('calculation-store', 'data'),
)
def update_results(data):
    if not data:
        return html.Div()
    
    results = []
    
    # Summary cards
    results.append(html.Div([
        html.H3("📊 Übersicht", className="mb-3"),
        html.Div([
            _create_info_card(
                f"CHF {data['monthly_income']:,.0f}",
                "Monatliches Einkommen",
                colors['primary']
            ),
            _create_info_card(
                f"CHF {data['pillar2']['monthly_total']:,.0f}",
                "2. Säule (Total/Monat)",
                colors['success']
            ),
            _create_info_card(
                f"CHF {data['pillar2']['estimated_capital']:,.0f}",
                "2. Säule bei Pensionierung",
                colors['warning']
            ),
            _create_info_card(
                f"{data['years_to_retirement']} Jahre",
                f"Bis Pensionierung (Alter {data['retirement_age']})",
                colors['danger']
            ),
        ], className="row"),
    ], className="card p-4 mb-4"))
    
    # Pillar 2 Details
    results.append(html.Div([
        html.H3("2️⃣ 2. Säule (Berufvorsorge)", className="mb-3"),
        html.Div([
            html.Div([
                html.P(f"Arbeitnehmer: CHF {data['pillar2']['monthly_employee']:,.2f}/Monat"),
                html.P(f"Arbeitgeber: CHF {data['pillar2']['monthly_employer']:,.2f}/Monat"),
                html.P(f"Total: CHF {data['pillar2']['monthly_total']:,.2f}/Monat"),
                html.P(f"Geschätztes Kapital: CHF {data['pillar2']['estimated_capital']:,.0f}"),
            ]),
        ]),
    ], className="card p-4 mb-4"))
    
    # Pillar 3a Scenarios
    results.append(html.Div([
        html.H3("3️⃣ 3a Sparlösungen (Gebundene Vorsorge)", className="mb-3"),
        html.Div(id='pillar3a-scenarios', children=_create_pillar3a_cards(data['pillar3a_scenarios'])),
    ], className="card p-4 mb-4"))
    
    # Pillar 3b Scenarios
    results.append(html.Div([
        html.H3("💰 3b Sparlösungen (Freie Vorsorge - unbegrenzt)", className="mb-3"),
        html.Div(id='pillar3b-scenarios', children=_create_pillar3b_cards(data['pillar3b_scenarios'])),
    ], className="card p-4 mb-4"))
    
    # Growth Chart
    results.append(html.Div([
        html.H3("📈 Vermögenswachstum (Best-Case Szenario mit 3a + 3b)", className="mb-3"),
        dcc.Graph(id='growth-chart', figure=_create_growth_chart(data)),
    ], className="card p-4 mb-4"))
    
    # Comparison Chart
    results.append(html.Div([
        html.H3("📊 Szenario-Vergleich (3a + 3b)", className="mb-3"),
        dcc.Graph(id='comparison-chart', figure=_create_comparison_chart(data)),
    ], className="card p-4 mb-4"))
    
    # Recommendations
    if data['summary'].get('recommendations'):
        results.append(html.Div([
            html.H3("💡 Empfehlungen", className="mb-3"),
            html.Ul([
                html.Li(rec, style={'marginBottom': '10px'})
                for rec in data['summary']['recommendations']
            ]),
        ], className="card p-4 mb-4", style={'borderLeft': f'4px solid {colors["warning"]}'}))
    
    return results


def _create_info_card(value: str, label: str, color: str):
    """Helper to create info cards"""
    return html.Div([
        html.Div(value, style={
            'fontSize': '24px',
            'fontWeight': 'bold',
            'color': color,
        }),
        html.Div(label, style={
            'fontSize': '14px',
            'color': colors['text'],
            'marginTop': '5px',
        }),
    ], className="col-md-3", style={
        'textAlign': 'center',
        'padding': '15px',
        'backgroundColor': colors['light'],
        'borderRadius': '5px',
        'marginBottom': '10px',
    })


def _create_pillar3a_cards(scenarios: Dict) -> List:
    """Create cards for each 3a scenario"""
    cards = []
    
    for scenario_name, data in scenarios.items():
        card = html.Div([
            html.H5(scenario_name),
            html.Div([
                html.Div(f"Monatlich: CHF {data['monthly']:,.2f}"),
                html.Div(f"Jährlich: CHF {data['annual']:,.2f}"),
                html.Div(f"Total Einzahlungen: CHF {data['contributions']:,.0f}"),
                html.Div(f"Gewinn aus Anlagen: CHF {data['gains']:,.0f}"),
                html.Div(
                    f"Bei Pensionierung: CHF {data['total_at_retirement']:,.0f}",
                    style={'fontWeight': 'bold', 'fontSize': '16px', 'marginTop': '10px', 'color': colors['success']}
                ),
            ], style={'fontSize': '13px', 'lineHeight': '1.8'}),
        ], className="col-md-4", style={
            'padding': '15px',
            'backgroundColor': colors['light'],
            'borderRadius': '5px',
            'marginBottom': '15px',
        })
        cards.append(card)
    
    return html.Div(cards, className="row")


def _create_pillar3b_cards(scenarios: Dict) -> List:
    """Create cards for each 3b scenario"""
    cards = []
    
    # Begrenzen auf maximal 8 Szenarien für bessere Darstellung
    scenarios_limited = dict(list(scenarios.items())[:8])
    
    for scenario_name, data in scenarios_limited.items():
        card = html.Div([
            html.H5(scenario_name),
            html.Div([
                html.Div(f"Monatlich: CHF {data['monthly']:,.2f}"),
                html.Div(f"Jährlich: CHF {data['annual']:,.2f}"),
                html.Div(f"Total Einzahlungen: CHF {data['contributions']:,.0f}"),
                html.Div(f"Gewinn aus Anlagen: CHF {data['gains']:,.0f}"),
                html.Div(
                    f"Bei Pensionierung: CHF {data['total_at_retirement']:,.0f}",
                    style={'fontWeight': 'bold', 'fontSize': '16px', 'marginTop': '10px', 'color': colors['warning']}
                ),
            ], style={'fontSize': '13px', 'lineHeight': '1.8'}),
        ], className="col-md-3", style={
            'padding': '15px',
            'backgroundColor': colors['light'],
            'borderRadius': '5px',
            'marginBottom': '15px',
        })
        cards.append(card)
    
    return html.Div(cards, className="row")


def _create_growth_chart(data: Dict):
    """Create growth chart"""
    # Get best scenarios for 3a and 3b
    best_3a_scenario = max(data['pillar3a_scenarios'].items(), key=lambda x: x[1]['total_at_retirement'])
    scenario_3a_name, scenario_3a = best_3a_scenario
    
    best_3b_scenario = max(data['pillar3b_scenarios'].items(), key=lambda x: x[1]['total_at_retirement']) if data['pillar3b_scenarios'] else None
    
    years = [y['year'] for y in scenario_3a['yearly_breakdown']]
    ages = [y['age'] for y in scenario_3a['yearly_breakdown']]
    balances_3a = [y['balance'] for y in scenario_3a['yearly_breakdown']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=ages,
        y=balances_3a,
        mode='lines+markers',
        name='3a Vermögen',
        line=dict(color=colors['primary'], width=2),
    ))
    
    # Add 3b if available
    if best_3b_scenario:
        balances_3b = [y['balance'] for y in best_3b_scenario[1]['yearly_breakdown']]
        fig.add_trace(go.Scatter(
            x=ages,
            y=balances_3b,
            mode='lines+markers',
            name='3b Vermögen',
            line=dict(color=colors['warning'], width=2),
        ))
    
    # Add total with pillar 2
    total_balances = [b + data['pillar2']['estimated_capital'] for b in balances_3a]
    if best_3b_scenario:
        balances_3b_all = [y['balance'] for y in best_3b_scenario[1]['yearly_breakdown']]
        total_balances = [b + d + data['pillar2']['estimated_capital'] for b, d in zip(balances_3a, balances_3b_all)]
    
    fig.add_trace(go.Scatter(
        x=ages,
        y=total_balances,
        mode='lines+markers',
        name='Total (2. Säule + 3a + 3b)',
        line=dict(color=colors['success'], width=3),
    ))
    
    fig.update_layout(
        xaxis_title="Alter",
        yaxis_title="Vermögen (CHF)",
        hovermode='x unified',
        template='plotly_white',
    )
    
    return fig


def _create_comparison_chart(data: Dict):
    """Create comparison chart for all scenarios combined"""
    scenarios_list = []
    totals = []
    
    # Kombiniere 3a + 3b beste Szenarien für Vergleich
    best_3a = max(data['pillar3a_scenarios'].items(), key=lambda x: x[1]['total_at_retirement'])
    best_3b = max(data['pillar3b_scenarios'].items(), key=lambda x: x[1]['total_at_retirement']) if data['pillar3b_scenarios'] else None
    
    scenarios_list.append(f"Nur 2. Säule")
    totals.append(data['pillar2']['estimated_capital'])
    
    scenarios_list.append(f"2. Säule + {best_3a[0]}")
    totals.append(best_3a[1]['total_at_retirement'] + data['pillar2']['estimated_capital'])
    
    if best_3b:
        scenarios_list.append(f"2. Säule + {best_3a[0]} + {best_3b[0]}")
        totals.append(best_3a[1]['total_at_retirement'] + best_3b[1]['total_at_retirement'] + data['pillar2']['estimated_capital'])
    
    fig = go.Figure(data=[
        go.Bar(
            x=scenarios_list,
            y=totals,
            marker=dict(color=totals, colorscale='Viridis'),
        )
    ])
    
    fig.update_layout(
        xaxis_title="Szenario",
        yaxis_title="Gesamtvermögen bei Pensionierung (CHF)",
        template='plotly_white',
        showlegend=False,
    )
    
    return fig


def run_dashboard(debug: bool = False, port: int = 8050):
    """Run the dashboard"""
    app.run(debug=debug, port=port, host='127.0.0.1')


if __name__ == '__main__':
    run_dashboard(debug=True)
