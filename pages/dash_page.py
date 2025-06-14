import dash
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from flask import Flask, request, g
from flask_restful import Resource, Api
import plotly.express as px
import pandas as pd
import pymongo
from pymongo import MongoClient
import simplejson
import requests
import json
import time
import json


client = MongoClient()
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
    yearly_df = pd.DataFrame(yearly_avgs)

    options = list(yearly_df.columns)

    options.remove("year")

    fig = px.bar(yearly_df, x="year", y="portfolio_nominal_mean")

    navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Profile", href="/profile", external_link=True)),
    ],
    )
    return html.Div([
    navbar,
    html.H4('Restaurant tips by day of week'),
    dcc.Dropdown(
        id="dropdown",
        options=options,
        clearable=False,
    ),
    dcc.Graph(
        id="graph",
        figure=fig),

    dcc.Store(id='intermediate-value', data=yearly_df.to_json(orient="records"))

    ]),
    

@callback(
    Output("graph", "figure"), 
    [Input("dropdown", "value"),
    Input('intermediate-value', 'data')],
    prevent_initial_call=True)
def change_graph(value, data, **_kwargs):
    df = pd.read_json(data)
    fig = px.bar(df, x="year", y=value)
    return fig
