import dash
from dash import Dash, html, dcc, callback, Input, Output, State, page_container
import plotly.express as px
import pandas as pd
import ssl
from flask import g


ssl._create_default_https_context = ssl._create_unverified_context

def init_app(url_path, server=None):
  
    app = Dash(server=g.cur_app, url_base_pathname=url_path, use_pages=True,
            suppress_callback_exceptions=True)

    return app.server
