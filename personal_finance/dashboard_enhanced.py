"""
Enhanced Dash Dashboard Application

Interaktives Dashboard mit erweiterten Eingaben für Finanzanalyse.
"""

import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objects as go
from typing import Dict, List
import json

from personal_finance.calculator import FinanceCalculator
from personal_finance import config
from personal_finance.deductions import DeductionsCalculator


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
        html.H1("🇨🇭 Swiss Personal Finance Planner", className="mb-2"),
        html.P("Schweizer Finanzplanung: 2. Säule, 3a & 3b mit interaktiven Schiebereglern"),
    ], className="container-fluid p-4", style={'backgroundColor': colors['primary'], 'color': 'white', 'marginBottom': '20px'}),
    
    # Main container
    html.Div([
        # Input Section
        html.Div([
            html.H3("📋 Persönliche Einstellungen", className="mb-4"),
            
            # Row 1: Gross Income, Age, Retirement
            html.Div([
                html.Div([
                    html.Label("Monatliches Bruttoeinkommen (CHF):"),
                    dcc.Input(
                        id='gross-income-input',
                        type='number',
                        placeholder='z.B. 6500',
                        value=6500,
                        min=0,
                        step=100,
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                    ),
                ], className="col-md-3"),
                
                html.Div([
                    html.Label("Aktuelles Alter:"),
                    dcc.Input(
                        id='current-age-input',
                        type='number',
                        value=35,
                        min=15,
                        max=100,
                        step=1,
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                    ),
                ], className="col-md-2"),
                
                html.Div([
                    html.Label("Pensionierungsalter:"),
                    dcc.Input(
                        id='retirement-age-input',
                        type='number',
                        value=65,
                        min=55,
                        max=75,
                        step=1,
                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                    ),
                ], className="col-md-2"),
                
                html.Div([
                    html.Label("Kanton (für Steuern):"),
                    dcc.Dropdown(
                        id='canton-select',
                        options=[
                            {'label': 'Zürich (ZH)', 'value': 'ZH'},
                            {'label': 'Bern (BE)', 'value': 'BE'},
                            {'label': 'Luzern (LU)', 'value': 'LU'},
                            {'label': 'Basel-Stadt (BS)', 'value': 'BS'},
                            {'label': 'Aargau (AG)', 'value': 'AG'},
                            {'label': 'St. Gallen (SG)', 'value': 'SG'},
                            {'label': 'Genf (GE)', 'value': 'GE'},
                            {'label': 'Waadt (VD)', 'value': 'VD'},
                        ],
                        value='ZH',
                        style={'width': '100%'}
                    ),
                ], className="col-md-2"),
            ], className="row", style={'marginBottom': '20px'}),
            
            # Gross to Net Summary
            html.Div(id='salary-summary', className="alert", style={'backgroundColor': colors['light'], 'padding': '15px', 'borderRadius': '4px', 'marginBottom': '20px'}),
            
            # Row 2: 2. Säule Input
            html.Div([
                html.H4("2️⃣ 2. Säule (Berufvorsorge)", style={'marginBottom': '15px'}),
                html.Div([
                    html.Div([
                        html.Label("Monatlicher Arbeitnehmer-Beitrag (CHF):"),
                        dcc.Input(
                            id='pillar2-employee-input',
                            type='number',
                            placeholder='z.B. 350',
                            value=350,
                            min=0,
                            step=10,
                            style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                        ),
                    ], className="col-md-3"),
                    html.Div([
                        html.Label("Startkapital (CHF):"),
                        dcc.Input(
                            id='pillar2-initial-capital-input',
                            type='number',
                            placeholder='z.B. 50000',
                            value=0,
                            min=0,
                            step=1000,
                            style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                        ),
                    ], className="col-md-3"),
                    html.Div([
                        html.Label("❌ Arbeitgeber-Beitrag (gleich wie oben)"),
                        html.Div(id='pillar2-employer-display', style={'padding': '10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '4px', 'fontWeight': 'bold'}),
                    ], className="col-md-3"),
                    html.Div([
                        html.Div(id='pillar2-note', style={'fontSize': '12px', 'color': colors['danger'], 'marginTop': '10px', 'fontStyle': 'italic'}),
                    ], className="col-md-3"),
                ], className="row"),
            ], className="card p-3 mb-3", style={'backgroundColor': '#f0f8ff', 'borderLeft': f'4px solid {colors["primary"]}'}),
            
            # Row 3: 3a Slider
            html.Div([
                html.H4(
                    f"3️⃣ 3a Sparlösungen (Gebundene Vorsorge - max. CHF {config.PILLAR3A_ANNUAL_MAX:,.0f}/Jahr)",
                    style={'marginBottom': '15px'},
                ),
                html.Div([
                    html.Div([
                        html.Label("Monatliche 3a Einzahlung:"),
                        html.Div(id='pillar3a-value-display', style={'fontSize': '18px', 'fontWeight': 'bold', 'color': colors['success'], 'marginBottom': '10px'}),
                        dcc.Slider(
                            id='pillar3a-slider',
                            min=0,
                            max=config.PILLAR3A_MONTHLY_MAX,
                            step=1,
                            value=300,
                            marks={
                                **{i: f'{i} CHF' for i in range(0, 601, 100)},
                                config.PILLAR3A_MONTHLY_MAX: "Max",
                            },
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ], className="col-md-9"),
                    html.Div([
                        html.Label("Startkapital 3a (CHF):"),
                        dcc.Input(
                            id='pillar3a-initial-capital-input',
                            type='number',
                            placeholder='z.B. 10000',
                            value=0,
                            min=0,
                            step=1000,
                            style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                        ),
                    ], className="col-md-3"),
                ], className="row"),
            ], className="card p-3 mb-3", style={'backgroundColor': '#f0fff4', 'borderLeft': f'4px solid {colors["success"]}'}),
            
            # Row 4: 3b Slider
            html.Div([
                html.H4("💰 3b Sparlösungen (Freie Vorsorge - unbegrenzt)", style={'marginBottom': '15px'}),
                html.Div([
                    html.Div([
                        html.Label("Monatliche 3b Einzahlung:"),
                        html.Div(id='pillar3b-value-display', style={'fontSize': '18px', 'fontWeight': 'bold', 'color': colors['warning'], 'marginBottom': '10px'}),
                        dcc.Slider(
                            id='pillar3b-slider',
                            min=0,
                            max=3000,
                            step=100,
                            value=500,
                            marks={i: f'{i} CHF' for i in range(0, 3001, 500)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ], className="col-md-9"),
                    html.Div([
                        html.Label("Startkapital 3b (CHF):"),
                        dcc.Input(
                            id='pillar3b-initial-capital-input',
                            type='number',
                            placeholder='z.B. 20000',
                            value=0,
                            min=0,
                            step=1000,
                            style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '4px', 'border': '1px solid #ddd'}
                        ),
                    ], className="col-md-3"),
                ], className="row"),
            ], className="card p-3 mb-3", style={'backgroundColor': '#fffbf0', 'borderLeft': f'4px solid {colors["warning"]}'}),
            
            html.Button(
                '📊 Berechnen',
                id='calculate-button',
                n_clicks=0,
                style={'width': '100%', 'padding': '12px', 'fontSize': '16px', 'fontWeight': 'bold', 'backgroundColor': colors['primary'], 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer', 'marginTop': '20px'}
            ),
            
            # Year projection slider
            html.Div([
                html.H4("🔮 Szenario Vorschau", style={'marginTop': '20px', 'marginBottom': '15px'}),
                html.Label("In wie vielen Jahren möchtest du die Übersicht sehen?"),
                html.Div([
                    dcc.Slider(
                        id='year-projection-slider',
                        min=0,
                        max=50,
                        step=1,
                        value=0,
                        marks={i: f'{i}y' for i in range(0, 51, 5)},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                ], style={'marginBottom': '10px'}),
                html.Div(id='year-projection-display', style={'fontSize': '14px', 'color': 'gray', 'marginTop': '10px'}),
            ], className="card p-3 mb-4", style={'backgroundColor': '#f9f9f9', 'borderLeft': f'4px solid {colors["warning"]}'}),
        ], className="card p-4 mb-4", style={'backgroundColor': colors['light']}),
        
        # Results Section
        html.Div(id='results-section', children=[]),
        
        # Charts Section
        html.Div([
            html.H3("📈 Visualisierungen", className="mb-4", style={'marginTop': '30px'}),
            html.Div([
                html.Div([
                    dcc.Graph(id='pillar-comparison-chart')
                ], className="col-md-6"),
                html.Div([
                    dcc.Graph(id='total-growth-chart')
                ], className="col-md-6"),
            ], className="row"),
            html.Div([
                html.Div([
                    dcc.Graph(id='monthly-contribution-chart')
                ], className="col-md-6"),
                html.Div([
                    dcc.Graph(id='deduction-breakdown-chart')
                ], className="col-md-6"),
            ], className="row"),
        ], id='charts-section', style={'display': 'none'}, className="container mt-4 mb-4"),
        
    ], className="container mt-4 mb-4"),
    
    # Store for calculations
    dcc.Store(id='calculation-store'),
    
], style={'backgroundColor': colors['background'], 'minHeight': '100vh'})


# Callbacks
@app.callback(
    Output('salary-summary', 'children'),
    Input('gross-income-input', 'value'),
    Input('pillar2-employee-input', 'value'),
    Input('canton-select', 'value'),
)
def update_salary_summary(gross_income, pillar2, canton):
    if not gross_income:
        return "Geben Sie ein Bruttoeinkommen ein"
    
    try:
        deductions_calc = DeductionsCalculator(
            gross_monthly_income=float(gross_income),
            employee_pillar2_contribution=float(pillar2) if pillar2 else 0,
            canton=canton
        )
        deductions = deductions_calc.calculate()
        
        return html.Div([
            html.Div(f"Brutto: CHF {gross_income:,.0f}/Monat", style={'fontSize': '14px', 'marginBottom': '5px'}),
            html.Div(f"Abzüge: AHV/IV/NBU ({deductions.ahv_iv_nbu:.0f}), ALV ({deductions.alv + deductions.alv_zusatz:.0f}), "
                    f"Krankenk. ({deductions.krankenkasse:.0f}), 2. Säule ({deductions.pensionskasse:.0f}), Steuern ({deductions.income_tax:.0f})",
                    style={'fontSize': '12px', 'marginBottom': '10px', 'color': colors['text']}),
            html.Div(
                f"✅ Netto: CHF {deductions.net_monthly_income:,.0f}/Monat ({(deductions.net_monthly_income/gross_income)*100:.1f}%)",
                style={'fontSize': '16px', 'fontWeight': 'bold', 'color': colors['success']}
            ),
        ])
    except:
        return "Fehler bei Berechnung"


@app.callback(
    Output('pillar2-employer-display', 'children'),
    Output('pillar2-note', 'children'),
    Input('pillar2-employee-input', 'value'),
)
def update_pillar2_employer(employee_contribution):
    if not employee_contribution:
        employee_contribution = 0
    
    employer = float(employee_contribution)
    note = f"Annahme: Arbeitgeber zahlt CHF {employer:,.0f} (gleich wie Arbeitnehmer) = CHF {employer*2:,.0f}/Monat Total"
    
    return f"CHF {employer:,.0f}/Monat", note


@app.callback(
    Output('pillar3a-value-display', 'children'),
    Input('pillar3a-slider', 'value'),
)
def update_pillar3a_display(value):
    monthly = min(value, config.PILLAR3A_MONTHLY_MAX)
    annual = monthly * 12
    limit_used = annual / config.PILLAR3A_ANNUAL_MAX * 100
    color = colors['success']
    return html.Div([
        html.Span(f"CHF {monthly:,.2f}/Monat", style={'color': color}),
        html.Br(),
        html.Span(f"(CHF {annual:,.0f}/Jahr, {limit_used:.0f}% des Limits)", style={'fontSize': '12px', 'color': 'gray'})
    ])


@app.callback(
    Output('pillar3b-value-display', 'children'),
    Input('pillar3b-slider', 'value'),
)
def update_pillar3b_display(value):
    annual = value * 12
    return html.Div([
        html.Span(f"CHF {value:,.0f}/Monat", style={'color': colors['warning']}),
        html.Br(),
        html.Span(f"(CHF {annual:,.0f}/Jahr)", style={'fontSize': '12px', 'color': 'gray'})
    ])


@app.callback(
    Output('year-projection-display', 'children'),
    [Input('year-projection-slider', 'value'),
     Input('calculation-store', 'data')],
)
def update_year_projection_display(years_projection, data):
    if not data:
        return "Berechne zuerst dein Szenario mit '📊 Berechnen'"
    
    r_monthly = 0.04 / 12
    
    # Calculate capital at projection year
    months = years_projection * 12
    def calc_at_year(initial, monthly, y):
        m = y * 12
        if r_monthly == 0:
            return initial + monthly * m
        initial_growth = initial * ((1 + r_monthly) ** m)
        monthly_growth = monthly * (((1 + r_monthly) ** m - 1) / r_monthly) if m > 0 else 0
        return initial_growth + monthly_growth
    
    p2 = calc_at_year(data['pillar2']['initial_capital'], data['pillar2']['monthly_total'], years_projection)
    p3a = calc_at_year(data['pillar3a']['initial_capital'], data['pillar3a']['monthly'], years_projection)
    p3b = calc_at_year(data['pillar3b']['initial_capital'], data['pillar3b']['monthly'], years_projection)
    total = p2 + p3a + p3b
    
    future_age = data['current_age'] + years_projection
    
    return html.Div([
        html.Div(f"📅 Szenario in {years_projection} Jahren (Alter: {future_age})", style={'fontWeight': 'bold', 'marginBottom': '8px'}),
        html.Div(f"2. Säule: CHF {p2:,.0f}", style={'marginBottom': '4px'}),
        html.Div(f"3a: CHF {p3a:,.0f}", style={'marginBottom': '4px'}),
        html.Div(f"3b: CHF {p3b:,.0f}", style={'marginBottom': '4px'}),
        html.Div(f"🎯 Total: CHF {total:,.0f}", style={'fontWeight': 'bold', 'color': colors['success'], 'marginTop': '8px', 'fontSize': '16px'}),
    ])


@app.callback(
    Output('calculation-store', 'data'),
    Input('calculate-button', 'n_clicks'),
    [
        State('gross-income-input', 'value'),
        State('current-age-input', 'value'),
        State('retirement-age-input', 'value'),
        State('canton-select', 'value'),
        State('pillar2-employee-input', 'value'),
        State('pillar2-initial-capital-input', 'value'),
        State('pillar3a-slider', 'value'),
        State('pillar3a-initial-capital-input', 'value'),
        State('pillar3b-slider', 'value'),
        State('pillar3b-initial-capital-input', 'value'),
    ],
    prevent_initial_call=True
)
def perform_calculation(n_clicks, gross_income, current_age, retirement_age, canton, pillar2, pillar2_initial, pillar3a, pillar3a_initial, pillar3b, pillar3b_initial):
    try:
        if not gross_income or current_age is None or retirement_age is None:
            return None
        
        # Default values if None
        gross_income = float(gross_income) if gross_income else 6500
        current_age = int(current_age) if current_age else 35
        retirement_age = int(retirement_age) if retirement_age else 65
        canton = canton if canton else 'ZH'
        pillar2 = float(pillar2) if pillar2 else 0
        pillar2_initial = float(pillar2_initial) if pillar2_initial else 0
        pillar3a = float(pillar3a) if pillar3a else 0
        pillar3a_initial = float(pillar3a_initial) if pillar3a_initial else 0
        pillar3b = float(pillar3b) if pillar3b else 0
        pillar3b_initial = float(pillar3b_initial) if pillar3b_initial else 0
        
        # Calculate net income from gross
        deductions_calc = DeductionsCalculator(
            gross_monthly_income=gross_income,
            employee_pillar2_contribution=pillar2,
            canton=canton
        )
        deductions = deductions_calc.calculate()
        net_monthly = deductions.net_monthly_income
        
        years = retirement_age - current_age
        months = years * 12
        r_monthly = 0.04 / 12  # Monthly rate from 4% annual
        
        # Calculate 3a capital with initial capital
        pillar3a_capital = 0
        if pillar3a > 0 or pillar3a_initial > 0:
            try:
                # FV = PV * (1 + r)^n + PMT * (((1 + r)^n - 1) / r)
                initial_growth = pillar3a_initial * ((1 + r_monthly) ** months)
                monthly_growth = 0
                if r_monthly == 0:
                    monthly_growth = pillar3a * months
                else:
                    monthly_growth = pillar3a * (((1 + r_monthly) ** months - 1) / r_monthly)
                pillar3a_capital = initial_growth + monthly_growth
            except:
                pillar3a_capital = 0
        
        # Calculate 3b capital with initial capital
        pillar3b_capital = 0
        if pillar3b > 0 or pillar3b_initial > 0:
            try:
                initial_growth = pillar3b_initial * ((1 + r_monthly) ** months)
                monthly_growth = 0
                if r_monthly == 0:
                    monthly_growth = pillar3b * months
                else:
                    monthly_growth = pillar3b * (((1 + r_monthly) ** months - 1) / r_monthly)
                pillar3b_capital = initial_growth + monthly_growth
            except:
                pillar3b_capital = 0
        
        # Calculate 2. Säule capital with initial capital
        employee_contrib_monthly = pillar2
        employer_contrib_monthly = pillar2  # Assumption: equal
        total_monthly_contrib = employee_contrib_monthly + employer_contrib_monthly
        
        # Future value with initial capital
        initial_growth = pillar2_initial * ((1 + r_monthly) ** months)
        monthly_growth = 0
        if r_monthly == 0:
            monthly_growth = total_monthly_contrib * months
        else:
            monthly_growth = total_monthly_contrib * (((1 + r_monthly) ** months - 1) / r_monthly)
        pillar2_capital = initial_growth + monthly_growth
        
        result = {
            'gross_monthly_income': gross_income,
            'net_monthly_income': net_monthly,
            'current_age': current_age,
            'retirement_age': retirement_age,
            'years_to_retirement': retirement_age - current_age,
            'canton': canton,
            
            'deductions': {
                'ahv_iv_nbu': float(deductions.ahv_iv_nbu),
                'alv': float(deductions.alv),
                'alv_zusatz': float(deductions.alv_zusatz),
                'krankenkasse': float(deductions.krankenkasse),
                'pensionskasse': float(deductions.pensionskasse),
                'income_tax': float(deductions.income_tax),
                'total': float(deductions.total_employee_deductions),
            },
            
            'pillar2': {
                'monthly_employee': pillar2,
                'monthly_employer': pillar2,
                'monthly_total': pillar2 * 2,
                'initial_capital': pillar2_initial,
                'estimated_capital': pillar2_capital,
            },
            
            'pillar3a': {
                'monthly': pillar3a,
                'annual': pillar3a * 12,
                'initial_capital': pillar3a_initial,
                'total_at_retirement': pillar3a_capital,
            },
            
            'pillar3b': {
                'monthly': pillar3b,
                'annual': pillar3b * 12,
                'initial_capital': pillar3b_initial,
                'total_at_retirement': pillar3b_capital,
            },
        }
        
        return result
    
    except Exception as e:
        print(f"Calculation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


@app.callback(
    Output('results-section', 'children'),
    Input('calculation-store', 'data'),
)
def update_results(data):
    if not data:
        return html.Div()
    
    results = []
    
    # Salary breakdown
    results.append(html.Div([
        html.H3("💰 Einkommensübersicht", className="mb-3"),
        html.Div([
            html.Div(f"Bruttolohn: CHF {data['gross_monthly_income']:,.0f}/Monat", className="col-md-4", style={'padding': '10px'}),
            html.Div(f"Nettolohn: CHF {data['net_monthly_income']:,.0f}/Monat", className="col-md-4", style={'padding': '10px', 'color': colors['success'], 'fontWeight': 'bold'}),
            html.Div(f"Abzüge: CHF {data['deductions']['total']:,.0f}/Monat ({(data['deductions']['total']/data['gross_monthly_income'])*100:.1f}%)", className="col-md-4", style={'padding': '10px'}),
        ], className="row"),
    ], className="card p-3 mb-3"))
    
    # Pillar breakdown
    total_monthly = (data['pillar2']['monthly_total'] + 
                     data['pillar3a']['monthly'] + 
                     data['pillar3b']['monthly'])
    
    total_at_retirement = (data['pillar2']['estimated_capital'] + 
                          data['pillar3a']['total_at_retirement'] + 
                          data['pillar3b']['total_at_retirement'])
    
    results.append(html.Div([
        html.H3("📊 Altersvorsorge Übersicht", className="mb-3"),
        html.Div([
            html.Div([
                html.H5("2️⃣ 2. Säule"),
                html.Div(f"Startkapital: CHF {data['pillar2']['initial_capital']:,.0f}", style={'fontSize': '12px', 'color': 'gray'}),
                html.Div(f"Monatlich: CHF {data['pillar2']['monthly_total']:,.0f}"),
                html.Div(f"Bei Pensionierung: CHF {data['pillar2']['estimated_capital']:,.0f}", style={'fontWeight': 'bold', 'marginTop': '5px', 'color': colors['primary']}),
            ], className="col-md-3", style={'padding': '15px', 'backgroundColor': colors['light'], 'borderRadius': '4px'}),
            
            html.Div([
                html.H5("3️⃣ 3a"),
                html.Div(f"Startkapital: CHF {data['pillar3a']['initial_capital']:,.0f}", style={'fontSize': '12px', 'color': 'gray'}),
                html.Div(f"Monatlich: CHF {data['pillar3a']['monthly']:,.0f}"),
                html.Div(f"Bei Pensionierung: CHF {data['pillar3a']['total_at_retirement']:,.0f}", style={'fontWeight': 'bold', 'marginTop': '5px', 'color': colors['success']}),
            ], className="col-md-3", style={'padding': '15px', 'backgroundColor': colors['light'], 'borderRadius': '4px'}),
            
            html.Div([
                html.H5("💰 3b"),
                html.Div(f"Startkapital: CHF {data['pillar3b']['initial_capital']:,.0f}", style={'fontSize': '12px', 'color': 'gray'}),
                html.Div(f"Monatlich: CHF {data['pillar3b']['monthly']:,.0f}"),
                html.Div(f"Bei Pensionierung: CHF {data['pillar3b']['total_at_retirement']:,.0f}", style={'fontWeight': 'bold', 'marginTop': '5px', 'color': colors['warning']}),
            ], className="col-md-3", style={'padding': '15px', 'backgroundColor': colors['light'], 'borderRadius': '4px'}),
            
            html.Div([
                html.H5("🎯 Total"),
                html.Div(f"Startkapital: CHF {(data['pillar2']['initial_capital'] + data['pillar3a']['initial_capital'] + data['pillar3b']['initial_capital']):,.0f}", style={'fontSize': '12px', 'color': 'gray'}),
                html.Div(f"Monatlich: CHF {total_monthly:,.0f}", style={'color': colors['primary'], 'fontWeight': 'bold'}),
                html.Div(f"Bei Pensionierung: CHF {total_at_retirement:,.0f}", style={'fontWeight': 'bold', 'marginTop': '5px', 'fontSize': '16px', 'color': colors['success']}),
            ], className="col-md-3", style={'padding': '15px', 'backgroundColor': colors['light'], 'borderRadius': '4px'}),
        ], className="row"),
    ], className="card p-3 mb-3"))
    
    return results


@app.callback(
    [Output('charts-section', 'style'),
     Output('pillar-comparison-chart', 'figure'),
     Output('total-growth-chart', 'figure'),
     Output('monthly-contribution-chart', 'figure'),
     Output('deduction-breakdown-chart', 'figure')],
    [Input('calculation-store', 'data'),
     Input('year-projection-slider', 'value')],
)
def update_charts(data, years_projection):
    if not data:
        return {'display': 'none'}, {}, {}, {}, {}
    
    # Ensure years_projection doesn't exceed retirement years
    years_projection = min(years_projection, data['years_to_retirement'])
    
    # Helper function to calculate capital at a given year
    def calc_capital_at_year(initial, monthly, years_count, r_monthly=0.04/12):
        months = years_count * 12
        if r_monthly == 0:
            return initial + monthly * months
        initial_growth = initial * ((1 + r_monthly) ** months)
        monthly_growth = monthly * (((1 + r_monthly) ** months - 1) / r_monthly) if months > 0 else 0
        return initial_growth + monthly_growth
    
    # Chart 1: Capital at Selected Year (or Retirement) Comparison
    pillars = ['2. Säule', '3a', '3b']
    
    p2_capital = calc_capital_at_year(
        data['pillar2']['initial_capital'],
        data['pillar2']['monthly_total'],
        years_projection
    )
    p3a_capital = calc_capital_at_year(
        data['pillar3a']['initial_capital'],
        data['pillar3a']['monthly'],
        years_projection
    )
    p3b_capital = calc_capital_at_year(
        data['pillar3b']['initial_capital'],
        data['pillar3b']['monthly'],
        years_projection
    )
    
    capitals = [p2_capital, p3a_capital, p3b_capital]
    
    title = f"Kapital nach {years_projection} Jahren"
    if years_projection == data['years_to_retirement']:
        title = "Kapital bei Pensionierung nach Säule"
    
    fig1 = go.Figure(data=[
        go.Bar(x=pillars, y=capitals, marker_color=['#3498db', '#e74c3c', '#f39c12'], text=[f'CHF {v:,.0f}' for v in capitals], textposition='outside')
    ])
    fig1.update_layout(
        title=title,
        xaxis_title="Säule",
        yaxis_title="CHF",
        template="plotly_white",
        hovermode='x unified'
    )
    
    # Chart 2: Growth over time (full trajectory)
    years = data['years_to_retirement']
    r_monthly = 0.04 / 12
    
    years_list = list(range(0, years + 1))
    pillar2_growth = []
    pillar3a_growth = []
    pillar3b_growth = []
    
    for y in years_list:
        p2 = calc_capital_at_year(data['pillar2']['initial_capital'], data['pillar2']['monthly_total'], y)
        p3a = calc_capital_at_year(data['pillar3a']['initial_capital'], data['pillar3a']['monthly'], y)
        p3b = calc_capital_at_year(data['pillar3b']['initial_capital'], data['pillar3b']['monthly'], y)
        
        pillar2_growth.append(p2)
        pillar3a_growth.append(p3a)
        pillar3b_growth.append(p3b)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=[data['current_age'] + y for y in years_list], y=pillar2_growth, mode='lines', name='2. Säule', line=dict(color='#3498db', width=2)))
    fig2.add_trace(go.Scatter(x=[data['current_age'] + y for y in years_list], y=pillar3a_growth, mode='lines', name='3a', line=dict(color='#e74c3c', width=2)))
    fig2.add_trace(go.Scatter(x=[data['current_age'] + y for y in years_list], y=pillar3b_growth, mode='lines', name='3b', line=dict(color='#f39c12', width=2)))
    
    # Add a vertical line at the current projection
    if years_projection > 0:
        fig2.add_vline(x=data['current_age'] + years_projection, line_dash="dash", line_color="gray", annotation_text=f"{years_projection}y", annotation_position="top left")
    
    fig2.update_layout(
        title="Kapitalentwicklung bis Pensionierung",
        xaxis_title="Alter",
        yaxis_title="CHF",
        template="plotly_white",
        hovermode='x unified'
    )
    
    # Chart 3: Monthly contributions
    contributions = [
        data['pillar2']['monthly_total'],
        data['pillar3a']['monthly'],
        data['pillar3b']['monthly']
    ]
    
    fig3 = go.Figure(data=[
        go.Bar(x=pillars, y=contributions, marker_color=['#3498db', '#e74c3c', '#f39c12'], text=[f'CHF {v:,.0f}' for v in contributions], textposition='outside')
    ])
    fig3.update_layout(
        title="Monatliche Beiträge pro Säule",
        xaxis_title="Säule",
        yaxis_title="CHF/Monat",
        template="plotly_white",
        hovermode='x unified'
    )
    
    # Chart 4: Deduction breakdown
    deductions = data['deductions']
    deduction_labels = ['AHV/IV/NBU', 'ALV', 'Krankenk.', 'Pensionsk.', 'Steuern']
    deduction_values = [
        deductions['ahv_iv_nbu'],
        deductions['alv'] + deductions['alv_zusatz'],
        deductions['krankenkasse'],
        deductions['pensionskasse'],
        deductions['income_tax']
    ]
    
    fig4 = go.Figure(data=[
        go.Pie(labels=deduction_labels, values=deduction_values, marker=dict(colors=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#95a5a6']))
    ])
    fig4.update_layout(
        title=f"Abzüge vom Bruttolohn (Total: CHF {deductions['total']:,.0f})"
    )
    
    return {'display': 'block'}, fig1, fig2, fig3, fig4


def run_dashboard(debug: bool = False, port: int = 8050):
    """Run the dashboard"""
    app.run(debug=debug, port=port, host='127.0.0.1')


if __name__ == '__main__':
    run_dashboard(debug=True)
