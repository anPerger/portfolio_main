import os
from flask import Flask, render_template, request, flash, redirect, session, jsonify
import requests
import webbrowser
from threading import Timer
from bson.json_util import dumps, loads
import json



app = Flask(__name__)
app.secret_key = "portfolio"

sim_microservice_url = "http://127.0.0.1:8001/"
acct_microservice_url = "http://127.0.0.1:8002/"
portfolio_microservice_url = "http://127.0.0.1:8003/"
analysis_microservice_url = "http://127.0.0.1:8004/analysis"
historic_microservice_url = "http://127.0.0.1:8005/return-historic-avgs"


# Configuration 
app.config["SESSION_PERMANENT"] = False     # Sessions expire when the browser is closed
app.config["SESSION_TYPE"] = "filesystem"     # Store session data in files


def call_sim_microservice(sim_request_string):
    response = requests.get(sim_request_string)
    return response.json().get("results")

def call_acct_microservice(acct_request_string):
    response = requests.get(acct_request_string)
    return response.json().get("results")

def call_portfolio_microservice(portfolio_request_string):
    response = requests.get(portfolio_request_string)
    return response.json().get("results")

def call_analysis_microservice(analysis_request_string):
    response = requests.get(analysis_request_string)
    return response.json().get("results")

def call_historic_microservice(historic_request_string):
    response = requests.get(historic_request_string)
    return response.json().get("results")


@app.route("/")
def home():
    session["name"] = None
    return render_template("index.html")


@app.route("/verify-account", methods=["GET", "POSt"])
def verify_account():

    username = request.form.get("username")
    password = request.form.get("password")

    verify_string = f"verify-account?username={username}&password={password}"
    verify_query = acct_microservice_url + verify_string
    
    results = call_acct_microservice(verify_query)

    if results["success"] == 0:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/")
    if results["success"] == 1:
        session["name"] = username
        return redirect("/profile")



@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("name"):
        return redirect("/")

    username = session["name"]
    
    fetch_profile_string = f"fetch-account?username={username}"
    fetch_profile_query = acct_microservice_url + fetch_profile_string

    user_data = call_acct_microservice(fetch_profile_query)

    return render_template("profile.html", user_data=user_data)



@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    return render_template("create-account.html")


@app.route("/profile-confirmation", methods=["GET", "POST"])
def profile_confirmation():

    username = request.form.get("username")
    password = request.form.get("password")

    create_account_string = f"create-account?username={username}&password={password}"
    create_account_query = acct_microservice_url + create_account_string

    results = call_acct_microservice(create_account_query)

    if results["success"] == 1:
        success_msg = "Your account has been created"
        flash(success_msg, "success")
        return redirect("/")
    else:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session["name"] = None
    return redirect("/")


@app.route("/update-profile", methods=["GET", "POST"])
def update_profile():
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]
    password = request.form.get("password")
    horizon = request.form.get("horizon")
    risk = request.form.get("risk")
    
    if not password:
        password = ""
    if not horizon:
        horizon = ""
    if not risk:
        risk = ""

    update_profile_string = f"update-account?username={username}&password={password}&horizon={horizon}&risk={risk}"
    update_profile_query = acct_microservice_url + update_profile_string

    results = call_acct_microservice(update_profile_query)


    if results["success"] == 1:
        success_msg = "Your profile has been updated"
        flash(success_msg, "success")
        return redirect("/build-default-portfolio")
    else:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/profile")

@app.route("/risk-survey", methods=["GET", "POST"])
def risk_survey():
    if not session.get("name"):
        return redirect("/")
    
    return render_template("risk-survey.html")

@app.route("/risk-survey-submit", methods=["GET", "POST"])
def risk_survey_submit():
    if not session.get("name"):
        return redirect("/")

    username = session["name"]
    q1 = int(request.form.get("q1"))
    q2 = int(request.form.get("q2"))
    q3 = int(request.form.get("q3"))
    q4 = int(request.form.get("q4"))
    q5 = int(request.form.get("q5"))
    q6 = int(request.form.get("q6"))
    q7 = int(request.form.get("q7"))
    q8 = int(request.form.get("q8"))
   
    risk_score = (q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8) 

    if risk_score < 13:
        risk = "Low"
    if (risk_score >= 13) & (risk_score < 19):
        risk = "Medium"
    if risk_score >= 19:
        risk = "High"

    risk_string = f"/update-account?username={username}&password=&horizon=&risk={risk}"
    risk_query = acct_microservice_url + risk_string
   
    results = call_acct_microservice(risk_query)

    if results["success"] == 1:
        success_msg = "Thanks for completing the survey. Based on your results you have a " + risk + " level of risk tolerence"
        flash(success_msg, "success")
        return redirect("/build-default-portfolio")
    else:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/profile")
        

@app.route("/build-default-portfolio", methods=["GET", "POST"])
def build_default_portfolio():
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]
    
    fetch_profile_string = f"fetch-account?username={username}"
    fetch_profile_query = acct_microservice_url + fetch_profile_string

    user_data = call_acct_microservice(fetch_profile_query)

    user_risk = user_data["risk"]
    user_horizon = user_data["horizon"]

    if user_risk == "none":
        error_msg = "Cannot build a portfolio for you without providing a risk profile"
        flash(error_msg, "error")
        return render_template("profile.html", user_data=user_data)
    if user_horizon == 0:
        error_msg = "Cannot build a portfolio for you without providing an investment time horizon"
        flash(error_msg, "error")
        return render_template("profile.html", user_data=user_data)

    if  user_risk == "High":
        if user_horizon == 1:
            stock_allocation = 0.2
            bond_allocation = 0.4
            cash_allocation = 0.4
        if (user_horizon > 1) & (user_horizon <= 5):
            stock_allocation = 0.6
            bond_allocation = 0.4
            cash_allocation = 0
        if (user_horizon > 5) & (user_horizon <= 10):
            stock_allocation = 0.8
            bond_allocation = 0.2
            cash_allocation = 0
        if (user_horizon > 10):
            stock_allocation = 1
            bond_allocation = 0
            cash_allocation = 0
    if  user_risk == "Medium":
        if user_horizon == 1:
            stock_allocation = 0.1
            bond_allocation = 0.45
            cash_allocation = 0.45
        if (user_horizon > 1) & (user_horizon <= 5):
            stock_allocation = 0.45
            bond_allocation = 0.45
            cash_allocation = 0.1
        if (user_horizon > 5) & (user_horizon <= 10):
            stock_allocation = 0.75
            bond_allocation = 0.25
            cash_allocation = 0
        if (user_horizon > 10):
            stock_allocation = 0.9
            bond_allocation = 0.1
            cash_allocation = 0
    if  user_risk == "Low":
        if user_horizon == 1:
            stock_allocation = 0
            bond_allocation = 0.5
            cash_allocation = 0.5
        if (user_horizon > 1) & (user_horizon <= 5):
            stock_allocation = 0.3
            bond_allocation = 0.5
            cash_allocation = 0.2
        if (user_horizon > 5) & (user_horizon <= 10):
            stock_allocation = 0.5
            bond_allocation = 0.5
            cash_allocation = 0
        if (user_horizon > 10):
            stock_allocation = 0.6
            bond_allocation = 0.4
            cash_allocation = 0

    portfolio_allocation_string = f"create-portfolio?username={username}&portfolio=Default-Portfolio&stocks={stock_allocation}&bonds={bond_allocation}&cash={cash_allocation}"
    
    portfolio_allocation_query = portfolio_microservice_url + portfolio_allocation_string

    results = call_portfolio_microservice(portfolio_allocation_query)

    if results["success"] == 1:
        success_msg = "A portfolio based on your investment profile has been created"
        flash(success_msg, "success")
        return redirect("/profile")
    else:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/profile")



@app.route("/custom-portfolio", methods=["GET", "POST"])
def custom_portfolio():
    if not session.get("name"):
        return redirect("/")
    return render_template("custom-portfolio.html")

@app.route("/save-portfolio", methods=["GET", "POST"])
def save_portfolio():
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    name = request.form.get("name")
    stocks = request.form.get("stocks")
    bonds = request.form.get("bonds")
    cash = request.form.get("cash")
    save_type = request.form.get("save-type")

    if not stocks:
        stocks = 0
    if not bonds:
        bonds = 0
    if not cash:
        cash = 0

    stocks = int(stocks)
    bonds = int(bonds)
    cash = int(cash)

    if name == "Default-Portfolio":
        error_msg = """You cannot use that name.\n 
        'Default-Portfolio' is reserved for the portfolio built for you based on your profile settings"""
        flash(error_msg, "error")
        if save_type == "edit":
            return redirect(f"/edit-portfolio/{name}")
        else:
            return redirect("/custom-portfolio")

    portfolio_sum = stocks + bonds + cash
    if portfolio_sum != 100:
        error_msg = "Your portfolio allocation must add up t0 100%"
        flash(error_msg, "error")
        if save_type == "edit":
            return redirect(f"/edit-portfolio/{name}")
        else:
            return redirect("/custom-portfolio")

    
    stocks = stocks / 100
    bonds = bonds / 100
    cash = cash / 100

    portfolio_allocation_string = f"create-portfolio?username={username}&portfolio={name}&stocks={stocks}&bonds={bonds}&cash={cash}"
    
    portfolio_allocation_query = portfolio_microservice_url + portfolio_allocation_string

    results = call_portfolio_microservice(portfolio_allocation_query)

    if results["success"] == 1:
        if save_type == "edit":
            success_msg = "Your portfolio has been modified"
        else:
            success_msg = "Your portfolio has been created"
        flash(success_msg, "success")
        return redirect(f"/portfolio-view/{name}")
    else:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/profile")



@app.route("/portfolio-list", methods=["GET", "POST"])
def portfolio_list():

    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    portfolio_search_string = f"return-portfolios?username={username}"
    portfolio_search_query = portfolio_microservice_url + portfolio_search_string

    results = call_portfolio_microservice(portfolio_search_query)

    custom_portfolios = []
    for portfolio in results:
        if portfolio["portfolio_name"] != "Default-Portfolio":
            custom_portfolios.append(portfolio)
        else:
            default_portfolio = portfolio


    return render_template("portfolio-list.html", default_portfolio=default_portfolio, custom_portfolios=custom_portfolios)



@app.route("/portfolio-view/<portfolio_name>", methods=["GET", "POST"])
def portfolio_view(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]
    
    portfolio_search_string = f"return-portfolio?username={username}&portfolio-name={portfolio_name}"
    portfolio_search_query = portfolio_microservice_url + portfolio_search_string

    portfolio = call_portfolio_microservice(portfolio_search_query)

    
    return render_template("portfolio-view.html", portfolio=portfolio)


@app.route("/delete-portfolio/<portfolio_name>", methods=["GET", "POST"])
def delete_portfolio(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]
    
    if portfolio_name == "Default-Portfolio":
        error_msg = "You cannot delete your default portfolio. If you would like to change your default portfolio you must edit your profile investment characteristics"
        flash(error_msg, "error")
        return redirect("/profile")
    
    portfolio_delete_string = f"delete-portfolio?username={username}&portfolio-name={portfolio_name}"
    portfolio_delete_query = portfolio_microservice_url + portfolio_delete_string

    results = call_portfolio_microservice(portfolio_delete_query)

    if results["success"] == 1:
        success_msg = "Your portfolio has been deleted"
        flash(success_msg, "success")
        return redirect("/portfolio-list")
    else:
        error_msg = results["error_msg"]
        flash(error_msg, "error")
        return redirect("/portfolio-list")


@app.route("/edit-portfolio/<portfolio_name>", methods=["GET", "POST"])
def edit_portfolio(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    if portfolio_name == "Default-Portfolio":
        error_msg = "If you would like to change your default portfolio you must edit your profile investment characteristics"
        flash(error_msg, "error")
        return redirect("/profile")
    
    portfolio_search_string = f"return-portfolio?username={username}&portfolio-name={portfolio_name}"
    portfolio_search_query = portfolio_microservice_url + portfolio_search_string

    portfolio = call_portfolio_microservice(portfolio_search_query)
        
    return render_template("portfolio-edit.html", portfolio=portfolio)
    


@app.route("/help", methods=["GET", "POST"])
def help():

    return render_template("help.html")


@app.route("/sim/<portfolio_name>", methods=["GET", "POST"])
def sim(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    fetch_profile_string = f"fetch-account?username={username}"
    fetch_profile_query = acct_microservice_url + fetch_profile_string

    user_data = call_acct_microservice(fetch_profile_query)
    horizon = user_data["horizon"]
    

    portfolio_search_string = f"return-portfolio?username={username}&portfolio-name={portfolio_name}"
    portfolio_search_query = portfolio_microservice_url + portfolio_search_string

    portfolio = call_portfolio_microservice(portfolio_search_query)

    hist_avgs = call_historic_microservice(historic_microservice_url)
    stock_avgs = hist_avgs["stocks"]
    bond_avgs = hist_avgs["bonds"]
    inflation_avgs = hist_avgs["inflation"]

    stock_yield = round(stock_avgs["yield"], 2) 
    stock_std = round(stock_avgs["std"], 2)
    stock_div = round(stock_avgs["dividend"], 2)

    bond_yield = round(bond_avgs["yield"], 2)
    bond_std = round(bond_avgs["std"], 2)
    bond_div = round(bond_avgs["dividend"], 2)

    inflation_rate = round(inflation_avgs["rate"], 2)
    inflation_std = round(inflation_avgs["std"], 2)
       
    return render_template("sim.html", horizon=horizon, portfolio=portfolio, 
                           stock_yield=stock_yield, stock_std=stock_std, stock_div=stock_div,
                           bond_yield=bond_yield, bond_std=bond_std, bond_div=bond_div,
                           inflation_rate=inflation_rate, inflation_std=inflation_std)

@app.route("/sim-portfolio/<portfolio_name>", methods=["GET", "POST"])
def sim_portfolio(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    fetch_profile_string = f"fetch-account?username={username}"
    fetch_profile_query = acct_microservice_url + fetch_profile_string

    user_data = call_acct_microservice(fetch_profile_query)

    hist_avgs = call_historic_microservice(historic_microservice_url)
    stock_avgs = hist_avgs["stocks"]
    bond_avgs = hist_avgs["bonds"]
    inflation_avgs = hist_avgs["inflation"]

    portfolio_search_string = f"return-portfolio?username={username}&portfolio-name={portfolio_name}"
    portfolio_search_query = portfolio_microservice_url + portfolio_search_string

    portfolio = call_portfolio_microservice(portfolio_search_query)

  
    user_stocks = str(portfolio["stocks"])
    user_bonds = str(portfolio["bonds"])
    user_cash = str(portfolio["cash"])

    stock_ret = request.form.get("stock-ret")
    stock_std = request.form.get("stock-std")
    stock_div = request.form.get("stock-div")

    bond_ret = request.form.get("bond-ret")
    bond_std = request.form.get("bond-std")
    bond_div = request.form.get("bond-div")

    inflation_rate = request.form.get("inflation-rate")
    inflation_std = request.form.get("inflation-std")

    horizon = request.form.get("horizon")
    num_sims = request.form.get("sims")
    principal = request.form.get("principal")

    reinvest = request.form.get("reinvest")

    if not stock_ret:
        stock_ret = stock_avgs["yield"]
    else:
        stock_ret = float(stock_ret) / 100
    if not stock_std:
        stock_std = stock_avgs["std"]
    else:
        stock_std = float(stock_std) / 100
    if not stock_div:
        stock_div = stock_avgs["dividend"]
    else:
        stock_div = float(stock_div) / 100
    if not bond_ret:
        bond_ret = bond_avgs["yield"]
    else:
        bond_ret = float(bond_ret) / 100
    if not bond_std:
        bond_std = bond_avgs["std"]
    else:
        bond_std = float(bond_std) / 100
    if not bond_div:
        bond_div = bond_avgs["dividend"]
    else:
        bond_div = float(bond_div) / 100
    if not inflation_rate:
        inflation_rate = inflation_avgs["rate"]
    else:
        inflation_rate = float(inflation_rate) / 100
    if not inflation_std:
        inflation_std = inflation_avgs["std"]
    else:
        inflation_std = float(inflation_std) / 100
    if not horizon:
        horizon = user_data["horizon"]
    if not num_sims:
        num_sims = 1000
    if not principal:
        principal = 1000
    if not reinvest:
        reinvest = True

    query_string = "/sim?user_stocks=" + str(user_stocks)
    query_string += "&user_bonds=" + str(user_bonds)
    query_string += "&user_cash=" + str(user_cash)
    query_string += "&user_horizon=" + str(horizon)
    query_string += "&stock_ret=" + str(stock_ret)
    query_string += "&stock_std=" + str(stock_std)
    query_string += "&stock_div=" + str(stock_div)
    query_string += "&bond_ret=" + str(bond_ret)
    query_string += "&bond_std=" + str(bond_std)
    query_string += "&bond_div=" + str(bond_div)
    query_string += "&inflation_rate=" + str(inflation_rate)
    query_string += "&inflation_std=" + str(inflation_std)
    query_string += "&sims=" + str(num_sims)
    query_string += "&principal=" + str(principal)
    query_string += "&reinvest=" + str(reinvest)
    query_string += "&portfolio_name=" + portfolio_name
    query_string += "&username=" + username

    sim_request_string = sim_microservice_url + query_string
    
    sim_results = call_sim_microservice(sim_request_string)
        
    if sim_results["success"] == 1:
        analysis_string = f"?username={username}&portfolio_name={portfolio_name}"
        analysis_query = analysis_microservice_url + analysis_string
        analysis_results = call_analysis_microservice(analysis_query)

    if analysis_results["success"] == 1:
        flash("Your simulation has been run", "success")
        return redirect(f"/sim-results/{portfolio_name}")
    else:
        flash(analysis_results["error_msg"], "error")
        return redirect(f"/sim/{portfolio_name}")

@app.route("/sim-results/<portfolio_name>", methods=["GET", "POST"])
def sim_results(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    check_string = f"/check-sim?username={username}&portfolio_name={portfolio_name}"
    check_query = sim_microservice_url + check_string

    sim_run = call_sim_microservice(check_query)

    if sim_run["success"] == 0:
        flash(sim_run["error_msg"], "error")
        return redirect(f"/sim/{portfolio_name}")
    else:
        return render_template("sim-results.html", username=username, portfolio_name=portfolio_name)


if __name__ == "__main__":
    app.run(port=8000, debug=True)

# def open_browser():
#     webbrowser.open_new("http://127.00.1:5000")

# if __name__ == "__main__":
#     Timer(2, open_browser).start()
#     app.run()