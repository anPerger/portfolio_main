import dash
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from flask import Flask, request, g
from flask_restful import Resource, Api
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import pymongo
from pymongo import MongoClient
import simplejson
import requests
import json
import mongo_creds 


username = f'{mongo_creds.username}'
password = f'{mongo_creds.password}'
cluster = f'{mongo_creds.clustername}'
auth = f'{mongo_creds.auth}'
# authSource = '<authSource>'
# authMechanism = '<authMechanism>'
uri = 'mongodb+srv://' + username + ':' + password + '@' + cluster + "." + auth + '.mongodb.net'
print(uri)
client = pymongo.MongoClient(uri)

portfolio_accts_db = client["portfolio_accts"]
users_col = portfolio_accts_db["users"]


sim_microservice_url = "http://127.0.0.1:8001/"

def call_sim_microservice(sim_request_string):
    response = requests.get(sim_request_string)
    return response.json().get("results")


dash.register_page(__name__, path_template="/report")


def layout(username=None, portfolio_name=None, key=None, **kwargs):

    check_string = f"/check-sim?username={username}&portfolio_name={portfolio_name}&key={key}"
    check_query = sim_microservice_url + check_string

 
    sim_run = call_sim_microservice(check_query)
    
    sim_results = sim_run["results"]
    yearly_avgs = sim_results["yearly_avgs"]
    # global yearly_df


    df = pd.DataFrame(yearly_avgs)
    options = list(df.columns)

    options.remove("year")
    options = [x for x in options if "_std" not in x]

    x_vals = list(df["year"])

    data = {"Cash": list(df["Cash Nominal"]),
            "Bonds": list(df["Bonds Nominal"]),
            "Stocks": list(df["Stocks Nominal"])}
    
    fig = go.Figure(go.Bar(x=x_vals, y=data["Stocks"], name='Stocks', hovertemplate="$%{y}<extra></extra>", hoverlabel=dict(align="left")))
    fig.add_trace(go.Bar(x=x_vals, y=data["Bonds"], name='Bonds', hovertemplate="$%{y}<extra></extra>", hoverlabel=dict(align="left")))
    fig.add_trace(go.Bar(x=x_vals, y=data["Cash"], name='Cash', hovertemplate="$%{y}<extra></extra>", hoverlabel=dict(align="left")))
    
    fig.update_layout(barmode='stack', xaxis={'categoryorder':'category ascending'})
    y_vals = list(df["Portfolio Nominal"])
    error_vals = list(df["Portfolio Nominal_std"])
    # fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, name="$", 
    #                             hovertemplate="$%{y}<extra></extra>",
    #                             hoverlabel=dict(align="left"))])
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        error_y=dict(type='data', array=error_vals, visible=True),
        mode='markers',
        marker_color='black',
        showlegend=True,
        name='Standard Deviation')
    )
    fig.update_layout(showlegend=True)
    fig.update_layout(
        title=dict(
        text="Portfolio Nominal"
        ),
        xaxis=dict(
            title=dict(
                text="Year"
            )
        ),
        yaxis=dict(
            title=dict(
                text="$ Value"
            )
        ),
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="RebeccaPurple"
        )
    )

    navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Profile", href="/profile", external_link=True)),
        dbc.NavItem(dbc.NavLink("Portfolio List", href="/portfolio-list", external_link=True)),
        dbc.NavItem(dbc.NavLink("Help", href="/help", external_link=True)),
        dbc.NavItem(dbc.NavLink("Logout", href="/", external_link=True)),
    ],
    )
    return html.Div([
    navbar,
    html.H1(f'{portfolio_name} Simulated Returns'),
    dcc.Dropdown(
        id="dropdown",
        options=options,
        clearable=False,
    ),
    dcc.Graph(
        id="graph",
        figure=fig),

    dcc.Store(id='intermediate-value', data=df.to_json(orient="records"))

    ]),
    

@callback(
    Output("graph", "figure"), 
    [Input("dropdown", "value"),
    Input('intermediate-value', 'data')],
    prevent_initial_call=True)
def change_graph(value, data, **_kwargs):
    df = pd.read_json(data)
    error_name = value + "_std"
    if value == "Inflation":
        y_label = "% Rate"
        multiplier = 100
        symbol = "%"
        hovertemplate = "%%{y}<extra></extra>"
    else:
        y_label = "$ Value"
        multiplier = 1
        symbol = "$"
        hovertemplate = "$%{y}<extra></extra>"

    y_vals = list(df[value])

    y_vals = [x * multiplier for x in y_vals]

    error_vals = list(df[error_name])

    error_vals = [x * multiplier for x in error_vals]
    x_vals = list(df["year"])


    if (value == "Portfolio Nominal") or (value == "Portfolio Real"):
        if (value == "Portfolio Nominal"):
            data = {"Cash": list(df["Cash Nominal"]),
                "Bonds": list(df["Bonds Nominal"]),
                "Stocks": list(df["Stocks Nominal"])}
        else:
            data = {"Cash": list(df["Cash Real"]),
                "Bonds": list(df["Bonds Real"]),
                "Stocks": list(df["Stocks Real"])}
    
        fig = go.Figure(go.Bar(x=x_vals, y=data["Stocks"], name='Stocks', hovertemplate="$%{y}<extra></extra>", hoverlabel=dict(align="left")))
        fig.add_trace(go.Bar(x=x_vals, y=data["Bonds"], name='Bonds', hovertemplate="$%{y}<extra></extra>", hoverlabel=dict(align="left")))
        fig.add_trace(go.Bar(x=x_vals, y=data["Cash"], name='Cash', hovertemplate="$%{y}<extra></extra>", hoverlabel=dict(align="left")))
        
        fig.update_layout(barmode='stack', xaxis={'categoryorder':'category ascending'}) 
    else:              
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, name=symbol, 
                                    hovertemplate=hovertemplate,
                                    hoverlabel=dict(align="left"))])
        
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        error_y=dict(type='data', array=error_vals, visible=True),
        mode='markers',
        marker_color='black',
        showlegend=True,
        name='Standard Deviation')
    )
    fig.update_layout(
        title=dict(
            text=f"{value}"
        ),
        xaxis=dict(
            title=dict(
                text="Year"
            )
        ),
        yaxis=dict(
            title=dict(
                text=f"{y_label}"
            )
        ),
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="RebeccaPurple"
        )
    )
    
    return fig
