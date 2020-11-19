from flask import Flask, url_for, render_template, request, redirect, session, send_file
# from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
import os
import sys
import sqlite3
from base import Base, Session, init_db
from models import User, Transaccion, Campanya
from datetime import datetime
import requests
from oauthlib.oauth2 import WebApplicationClient
from flask_restful import Resource, Api
from web3 import Web3
import json
from forms import EnviarUDCForm, CrearCampanaForm, AccionesForm
import cryptocompare
import qrcode
import re

ropsten_url = "https://ropsten.infura.io/v3/834fad9971d14e4cb81715ed0f7adb0a"
infura_secret = "0bc36d15c0a841b7835509d9b9fd0f52"
WEB3_INFURA_PROJECT_ID = "834fad9971d14e4cb81715ed0f7adb0a"
GOOGLE_CLIENT_ID = "543251693947-uuomjheqpj6piup81pvbahrc3nu25o9m.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "60ajlp1BRZMnryrOBFD1sMkz"
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
test_address = "0x99AD62313b591405Ba1C51aa50294245A36F1289"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config["SECRET_KEY"] = app.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost:5432/deustoCoin'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# login_manager = LoginManager(app)
# login_manager.login_view = "login"
# db = SQLAlchemy(app)

api = Api(app)
web3 = Web3(Web3.HTTPProvider(ropsten_url))
balance = web3.eth.getBalance(test_address)
valorUDC = cryptocompare.get_price('ETH').get('ETH').get('EUR')
int_balance = float(web3.fromWei(balance, "ether")) * valorUDC
init_db()
str_abi = '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"INITIAL_SUPPLY","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_value","type":"uint256"}],"name":"burn","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_value","type":"uint256"}],"name":"burnFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[{"name":"_name","type":"string"},{"name":"_symbol","type":"string"},{"name":"_decimals","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_burner","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Burn","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]'
abi = json.loads(str_abi)
address = "0x4BFBa4a8F28755Cb2061c413459EE562c6B9c51b"  # OMG Network
contract = web3.eth.contract(address=address, abi=abi)
totalSupply = contract.functions.totalSupply().call()
destname = contract.functions.name().call()
destsymbol = contract.functions.symbol().call()


oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='543251693947-uuomjheqpj6piup81pvbahrc3nu25o9m.apps.googleusercontent.com',
    client_secret='60ajlp1BRZMnryrOBFD1sMkz',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    # This is only needed if using openId to fetch user info
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

def get_balance(test_address):
    web3 = Web3(Web3.HTTPProvider(ropsten_url))
    balance = web3.eth.getBalance(test_address)
    valorUDC = cryptocompare.get_price('ETH').get('ETH').get('EUR')
    balancefloat = float(web3.fromWei(balance, "ether")) * valorUDC
    print("Tu balance es de %.2f UDC" % balancefloat)
    return balancefloat

def sendCoins(dest, amount):
    destUser = User.get_by_email(dest)
    account_2 = destUser.blockHash
    print(account_2)
    private_key = "e49aed1a79c5f2c703b5651dd09c840d3193175fd748fbea37e00ce8d83a3c7d"
    nonce = web3.eth.getTransactionCount(test_address)
    float_amount = float(amount)/valorUDC
    tx = {
        'nonce': nonce,
        'to': account_2,
        'value': web3.toWei(float_amount, 'ether'),
        'gas': 50000,
        'gasPrice': web3.toWei(100, 'gwei') #gas: rapidez de transaccion
    }
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    
    s = Session()
    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")
    t = Transaccion(timestampStr,tx_hash,"Universidad de Deusto",dest,amount)
    print("Funciona la transaccion desde aqui")
    s.add(t)
    s.commit()

@app.route('/')
def home():
    return render_template("login.html")

@app.route('/login')
def login():
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    print((dict(user_info)), file=sys.stderr)
    session['email'] = user_info['email']
    session['given_name'] = user_info['given_name']
    session['name'] = user_info['name']
    session['picture'] = user_info['picture']
    session['token'] = token
    user = User.get_by_email(session['email'])
    if 'campId' in session and user != None:
        print(session['campId'])
        print("Si hay campaña para printear")
        cReward = Campanya.getCampaignById(session['campId'])
        sendCoins(user_info['email'], cReward.recompensa)
        return render_template("recompensa.html", name=session['name'], campanya = cReward, email = session['email'])
    else:
        if user != None:
            if user.role == 'Profesor':
                return redirect('/wallet')
            if user.role == 'Campaña':
                return redirect('/campanya')         
        else:
            return redirect('/register')
        print("No hay campaña")


@app.route('/register', methods=['GET', 'POST'])
def register():
    print(dict)
    email = dict(session).get('email', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    if request.method == "POST":
        print("postttt")
        nombre = request.form['nombre'] 
        email = request.form['email']
        blockchainAddr = request.form['blockAddr']
        session['blockchainAddr'] = blockchainAddr
        rol = request.form['rol']
        org = request.form['organizacion']

        s = Session()
        u = User(nombre, email, blockchainAddr, picture, rol, org)
        s.add(u)
        s.commit()
        if rol == 'Profesor':
            return redirect('/wallet')
        if rol == 'Campaña':
            return redirect('/campanya')
    else:
        return render_template("register.html", email = email, nombre = name)
    

@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    form = EnviarUDCForm()
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    salary = get_balance(user.blockHash)
    if form.validate_on_submit():
        account_1 = user.blockHash
        destUser = User.get_by_email(request.form['destino'])
        account_2 = destUser.blockHash
        print(account_2)
        private_key = "e49aed1a79c5f2c703b5651dd09c840d3193175fd748fbea37e00ce8d83a3c7d"
        nonce = web3.eth.getTransactionCount(account_1)
        float_amount = float(request.form['cantidad'])/valorUDC
        tx = {
            'nonce': nonce,
            'to': account_2,
            'value': web3.toWei(float_amount, 'ether'),
            'gas': 50000,
            'gasPrice': web3.toWei(100, 'gwei') #gas: rapidez de transaccion
        }
        signed_tx = web3.eth.account.signTransaction(tx, private_key)
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        s = Session()
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")
        t = Transaccion(timestampStr,tx_hash,email,request.form['destino'],request.form['cantidad'])
        s.add(t)
        s.commit()
    else:
        print("form no submitteado")
    given_name = dict(session).get('given_name', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    transacciones = Transaccion.getTransactions(email)
    campanyas = Campanya.getAllCampaigns()
    return render_template('tab1cartera.html', title='Cartera', wallet=salary, email=email, name=given_name, w3=web3, form = form, picture=picture, user = user, transacciones = transacciones, campanyas = campanyas)

@app.route('/campanya', methods=['GET', 'POST'])
def campanya():
    form = CrearCampanaForm()
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    campanyas = Campanya.getCampaigns(user.organizacion)
    salary = get_balance(test_address)
    print(campanyas)
    s = Session()
    if form.validate_on_submit():
        c = Campanya(request.form['nomCamp'],user.organizacion,request.form['desc'],request.form['recompensa'])
        s.add(c)
        s.commit()
        intId = Campanya.getIdByName(c.nombre)
        qr = qrcode.make(url_for("redeem", campanya_id=intId, _external=True))
        qr.save('./static/qr/'+ str(intId) + ".png")
    return render_template('campanya.html', title='Campaña', wallet=salary, email=email, name=given_name, w3=web3, form = form, picture=picture, user = user, campanyas = campanyas)

@app.route('/campanyalumnos', methods=['GET', 'POST'])
def campanyalumnos():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    campanyas = Campanya.getAllCampaigns()
    return render_template('campanyalumnos.html', title='Campaña', wallet=int_balance, email=email, name=given_name, w3=web3, picture=picture, user = user, campanyas = campanyas)

@app.route('/historialtrans', methods=['GET', 'POST'])
def historialtrans():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    transacciones = Transaccion.getTransactions(user.email)
    return render_template('historialtrans.html', title='Campaña', wallet=int_balance, email=email, name=name, w3=web3, picture=picture, user = user, transacciones = transacciones)

@app.route('/editor', methods=['GET', 'POST'])
def editor():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    campanyas = Campanya.getCampaigns(user.organizacion)
    s = Session()
    if request.method == 'POST':
        if 'editar' in request.form:
            return redirect(url_for('editorCamp' ,campanya_id=request.form['id']))
        elif 'eliminar' in request.form:
            query = s.query(Campanya)
            pk = request.form['id']
            query = query.filter(Campanya.id==pk).first()
            s.delete(query)
            s.commit()
    return render_template('admincampanyas.html', title='Campaña', wallet=int_balance, email=email, name=given_name, w3=web3, picture=picture, user = user, campanyas = campanyas)

@app.route('/editor/<int:campanya_id>', methods=["GET", "POST"])
def editorCamp(campanya_id):
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    user = User.get_by_email(email)

    s = Session()  
    query = s.query(Campanya)
    campanya = query.filter(Campanya.id==campanya_id).first()
    if request.method == 'POST':
        dictupdate = {Campanya.nombre: request.form['nombre'], Campanya.descripcion: request.form['descripcion'], Campanya.recompensa: float(request.form['recompensa'])}
        query.filter(Campanya.id == campanya_id).update(dictupdate, synchronize_session=False)
        s.commit()
    return render_template("editorcampanya.html", campanya = campanya, email=email, name=given_name, picture=picture, user=user)

@app.route('/qr/<int:campanya_id>')
def qr(campanya_id):
    path = 'static/qr/'+ str(campanya_id) + ".png"
    return send_file(path, as_attachment=True)

@app.route('/redeem/<int:campanya_id>', methods=["GET", "POST"])
def redeem(campanya_id):
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize',_external=True)
    session['campId'] = campanya_id
    return google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)

