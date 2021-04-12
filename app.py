from flask import Flask, url_for, render_template, request, redirect, Response, session, send_file
from flask_babel import Babel, gettext
from authlib.integrations.flask_client import OAuth
from base import Session, init_db
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from models import User, Transaccion, Accion, Campanya, KPIporFechas, Oferta
from datetime import datetime
from web3 import Web3
from forms import EnviarUDCForm, CrearCampForm, CrearOfertaForm
import cryptocompare
import io
import ipfshttpclient
import qrcode
import os

app = Flask(__name__)
app.config['BABEL_DEFAULT_LOCALE'] = 'es'
babel = Babel(app)
app.config.from_object("config.Config")
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config["SECRET_KEY"] = app.secret_key
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
test_address = app.config['TEST_ADDRESS']
private_key = app.config['PRIVATE_KEY']
web3 = Web3(Web3.HTTPProvider(app.config['ROPSTEN_URL']))
valorUDC = cryptocompare.get_price('ETH').get('ETH').get('EUR')
init_db()

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'es')



def get_balance(test_address):
    web3 = Web3(Web3.HTTPProvider(app.config['ROPSTEN_URL']))
    balance = web3.eth.getBalance(test_address)
    valorUDC = cryptocompare.get_price('ETH').get('ETH').get('EUR')
    balancefloat = float(web3.fromWei(balance, "ether")) * valorUDC
    return balancefloat


def sendCoins(dest, amount, imgHash, urlProof):
    destUser = User.get_by_email(dest)
    account_2 = destUser.blockHash

    nonce = web3.eth.getTransactionCount(test_address)

    accion = Accion.getActionById(session['accionId'])
    float_amount = float(amount) / valorUDC
    tx = {
        'chainId': 3,  # es 3 para Ropsten
        'nonce': nonce,
        'to': account_2,
        'value': web3.toWei(float_amount, 'ether'),
        'gas': 21000,
        'gasPrice': web3.toWei(50, 'gwei')
    }
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    s = Session()
    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("%d-%m-%Y (%H:%M:%S.%f)")
    t = Transaccion(timestampStr, tx_hash, accion.empresa, dest, accion.campanya_id, amount, imgHash, urlProof)
    s.add(t)
    s.commit()
    query = s.query(Accion)
    kpi = request.form['kpi']
    dictupdate = {Accion.kpi: Accion.kpi + kpi}
    query.filter(Accion.id == accion.id).update(dictupdate, synchronize_session=False)
    s.commit()
    s.close()

def offerTransaction(rem, dest, amount):
    destUser = User.get_by_email(dest)
    account_2 = destUser.blockHash
    nonce = web3.eth.getTransactionCount(test_address)
    float_amount = float(amount) / valorUDC
    tx = {
        'chainId': 3,  # es 3 para Ropsten
        'nonce': nonce,
        'to': account_2,
        'value': web3.toWei(float_amount, 'ether'),
        'gas': 21000,
        'gasPrice': web3.toWei(50, 'gwei')
    }
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    s = Session()
    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("%d-%m-%Y (%H:%M:%S.%f)")
    t = Transaccion(timestampStr, tx_hash, rem, destUser.organizacion, None, amount, "", "")
    s.add(t)
    s.commit()
    s.close()

def create_figure(id):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    accion = Accion.getActionById(id)
    data = KPIporFechas.getGraphData(id)
    titulo = data.get("name")
    axis.set_title(titulo + " - " + accion.indicadorKpi)
    axis.set_ylim(0, accion.kpiObj)
    axis.set_xlabel("Fecha")
    axis.set_ylabel(accion.indicadorKpi)
    results = data.get("results")[::-1]
    xs = [x.fecha for x in results]
    ys = [y.kpi for y in results]
    axis.plot(xs, ys)
    return fig

@app.route('/')
def home():
    KPIporFechas.saveTodaysKPI()
    create_figure(1)
    return render_template("login.html")

@app.route('/language/<lang>')
def language(lang):
    session['lang'] = lang
    return redirect(request.referrer)


@app.route('/login')
def login():
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    client = ipfshttpclient.connect(app.config['IPFS_CONNECT_URL'])
    user = User.get_by_email(session['email'])
    try:
        urlProof = request.form['proof']
    except:
        urlProof = ""
    file = request.files['filename']
    res = client.add(file)
    client.close()
    cReward = Accion.getActionById(session['accionId'])
    sendCoins(session['email'], cReward.recompensa, res['Hash'], urlProof)
    del session['accionId']
    return render_template("recompensa.html", name=session['name'], accion=cReward, email=session['email'], user=user)


@app.route('/authorize')
def authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    session['email'] = user_info['email']
    session['given_name'] = user_info['given_name']
    session['name'] = user_info['name']
    session['picture'] = user_info['picture']
    session['token'] = token
    user = User.get_by_email(session['email'])

    if 'accionId' in session and user != None:
        cReward = Accion.getActionById(session['accionId'])
        if cReward != None:
            return render_template("subirimagen.html", name=session['name'], cReward=cReward, email=session['email'],
                               session=session, user=user, accionId=cReward)
        else:
            return redirect('/wallet')
    if 'offerId' in session and user != None:
        offer = Oferta.getOfferById(session['offerId'])
        if offer != None:
            dest = User.getCompanyBlockAddr(offer.empresa).email
            offerTransaction(session['email'], dest, offer.precio)
            return render_template("pago.html", name=session['name'], offer=offer, email=session['email'],
                                   session=session, user=user)
        else:
            return redirect('/wallet')
    else:
        if user != None:
            if user.role == 'Alumno':
                return redirect('/wallet')
            else:
                return redirect('/accion')

        else:
            return redirect('/register')


@app.route('/register', methods=['GET', 'POST'])
def register():
    email = dict(session).get('email', None)
    name = dict(session).get('name', None)
    picture = dict(session).get('picture', None)
    if request.method == "POST":
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
        if rol == 'Alumno':
            return redirect('/wallet')
        if rol == 'Promotor':
            return redirect('/accion')
    else:
        return render_template("register.html", email=email, nombre=name)


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
        nonce = web3.eth.getTransactionCount(account_1)
        float_amount = float(request.form['cantidad']) / valorUDC
        tx = {
            'chainId': 3,
            'nonce': nonce,
            'to': account_2,
            'value': web3.toWei(float_amount, 'ether'),
            'gas': 50000,
            'gasPrice': web3.toWei(100, 'gwei')
        }
        signed_tx = web3.eth.account.signTransaction(tx, private_key)
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        s = Session()
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")
        t = Transaccion(timestampStr, tx_hash, email, request.form['destino'], None, request.form['cantidad'], "", "")
        s.add(t)
        s.commit()
    given_name = dict(session).get('given_name', None)
    transacciones = Transaccion.getTransactions(email)
    acciones = Accion.getAllActions()
    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('tab1cartera.html', title='Cartera', wallet=salary, email=email, name=given_name, w3=web3,
                           form=form, user=user, transacciones=transacciones, acciones=acciones)

@app.route('/redeemOffer/<int:offer_id>')
def redeemOffer(offer_id):
    offer = Oferta.getOfferById(offer_id)
    user = User.get_by_email(session['email'])
    dest = User.getCompanyBlockAddr(offer.empresa).email
    offerTransaction(session['email'], dest, offer.precio)
    return render_template("pago.html", name=session['name'], offer=offer, email=session['email'],
                           session=session, user=user)

@app.route('/accion', methods=['GET', 'POST'])
def accion():
    form = CrearCampForm()
    form2 = CrearOfertaForm()
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)

    if user.role == "Promotor":
        campanyas = Campanya.getCampaigns(user.organizacion)
        acciones = Accion.getActions(user.organizacion)
        ofertas = Oferta.getOffers(user.organizacion)
    elif user.role == "Administrador":
        campanyas = Campanya.getAllCampaigns()
        acciones = Accion.getAllActions()
        ofertas = Oferta.getAllOffers()
    else:
        return redirect("/login")

    salary = get_balance(user.blockHash)
    if form.validate_on_submit() and form.crearCamp.data:
        s = Session()
        if user.role == "Promotor":
            c = Campanya(request.form['nomCamp'], user.organizacion, request.form['desc'])
        elif user.role == "Administrador":
            c = Campanya(request.form['nomCamp'], request.form['empresa'], request.form['desc'])
        s.add(c)
        s.commit()
    elif form2.validate_on_submit() and form2.crearOf.data:
        nombre = request.form['nomOferta']
        s = Session()
        if user.role == "Promotor":
            o = Oferta(request.form['nomOferta'], user.organizacion, request.form['desc'], request.form['precio'])
        elif user.role == "Administrador":
            o = Oferta(request.form['nomOferta'], request.form['empresa'], request.form['desc'], request.form['precio'])
        s.add(o)
        s.commit()
        intId = Oferta.getIdByName(nombre)
        qr = qrcode.make(url_for("pay", offer_id=intId, _external=True))
        qr.save('./static/qr/ofertas/' + str(intId) + ".png")

    if request.method == 'POST' and 'crearAccion' in request.form:
        nombre = request.form['nombre']
        desc = request.form['desc']
        recompensa = request.form['recompensa']
        indKpi = request.form['kpi']
        kpiObj = request.form['obj']
        camp = request.form['campanya']
        s = Session()
        a = Accion(nombre, user.organizacion, desc, recompensa, indKpi, kpiObj, camp)
        s.add(a)
        s.commit()
        intId = Accion.getIdByName(nombre)
        qr = qrcode.make(url_for("redeem", accion_id=intId, _external=True))
        qr.save('./static/qr/acciones/' + str(intId) + ".png")

    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    #Borro las keys para evitar conflictos con cookies

    return render_template('accion.html', title='Acción', wallet=salary, email=email, name=given_name, w3=web3,
                           form=form, form2=form2, user=user, acciones=acciones, campanyas=campanyas, ofertas=ofertas)


@app.route('/accionalumnos', methods=['GET', 'POST'])
def accionalumnos():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    salary = get_balance(user.blockHash)
    acciones = Accion.getAllActions()
    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('accionalumnos.html', title='Acción', wallet=salary, email=email, name=given_name, w3=web3,
                           user=user, acciones=acciones)

@app.route('/ofertas', methods=['GET', 'POST'])
def ofertas():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    salary = get_balance(user.blockHash)
    ofertas = Oferta.getAllOffers()
    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('ofertas.html', title='Oferta', wallet=salary, email=email, name=given_name, w3=web3,
                           user=user, ofertas=ofertas)

@app.route('/historialtrans', methods=['GET', 'POST'])
def historialtrans():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    salary = get_balance(user.blockHash)
    name = dict(session).get('name', None)
    if user.role == "Alumno":
        transacciones = Transaccion.getTransactions(user.email)
    else:
        transacciones = Transaccion.getAllTransactions()
    for t in transacciones:
        campId = t.campanya
        try:
            t.campanya = Campanya.getCampaignById(campId).nombre
        except:
            if "@" not in str(t.destinatario):
                t.campanya = "Pago por oferta"
            else:
                t.campanya = "Envío de UDCoins"

    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('historialtrans.html', title='Acción', wallet=salary, email=email, name=name, w3=web3,
                           user=user, transacciones=transacciones)


@app.route('/editor/<int:campanya_id>', methods=['GET', 'POST'])
def editor(campanya_id):
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    acciones = Accion.getActionsOfCampaign(campanya_id)
    campanya = Campanya.getCampaignById(campanya_id)
    salary = get_balance(user.blockHash)
    s = Session()
    if request.method == 'POST':
        if 'editarAcc' in request.form:
            print("hay editarAcc")
            id = request.form['accion_id']
            # action="{{ url_for('editorAccion', accion_id=a.id) }}"
            return redirect(url_for('editorAccion', accion_id=request.form['accion_id']))
        elif 'eliminarAcc' in request.form:
            query = s.query(Accion)
            pk = request.form['accion_id']
            query = query.filter(Accion.id == pk).first()
            s.delete(query)
            s.commit()

    return render_template('adminacciones.html', title='Acción', wallet=salary, email=email, name=given_name, w3=web3,
                           user=user, acciones=acciones, campanya=campanya)


@app.route('/plot<int:campanya_id>.png')
def plot_png(campanya_id):
    fig = create_figure(campanya_id)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


@app.route('/editorC', methods=['GET', 'POST'])
def editorC():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    if user.role == "Promotor":
        campanyas = Campanya.getCampaigns(user.organizacion)
    if user.role == "Administrador":
        campanyas = Campanya.getAllCampaigns()
    salary = get_balance(user.blockHash)
    s = Session()
    if request.method == 'POST':
        if 'editar' in request.form:
            return redirect(url_for('editorCamp', campanya_id=request.form['id']))
        elif 'eliminar' in request.form:
            query = s.query(Campanya)
            pk = request.form['id']
            query = query.filter(Campanya.id == pk).first()
            s.delete(query)
            s.commit()
        elif 'verAcc' in request.form:
            return redirect(url_for('editor', campanya_id=request.form['id']))
    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('admincampanyas.html', title='Campañas', wallet=salary, email=email, name=given_name,
                           w3=web3, user=user, campanyas=campanyas)

@app.route('/editorO', methods=['GET', 'POST'])
def editorO():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    if user.role == "Promotor":
        ofertas = Oferta.getOffers(user.organizacion)
    if user.role == "Administrador":
        ofertas = Oferta.getAllOffers()
    salary = get_balance(user.blockHash)
    s = Session()
    if request.method == 'POST':
        if 'editarO' in request.form:
            return redirect(url_for('editorOferta', offer_id=request.form['id']))
        elif 'eliminarO' in request.form:
            query = s.query(Oferta)
            pk = request.form['id']
            query = query.filter(Oferta.id == pk).first()
            s.delete(query)
            s.commit()
    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('adminofertas.html', title='Ofertas', wallet=salary, email=email, name=given_name,
                           w3=web3, user=user, ofertas=ofertas)

@app.route('/editarAcc/<int:accion_id>', methods=["GET", "POST"])
def editorAccion(accion_id):
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    s = Session()
    query = s.query(Accion)
    accion = query.filter(Accion.id == accion_id).first()
    if request.method == 'POST' and 'actualizarA' in request.form:
        dictupdate = {Accion.nombre: request.form['nombre'], Accion.descripcion: request.form['descripcion'],
                      Accion.recompensa: float(request.form['recompensa'])}
        query.filter(Accion.id == accion_id).update(dictupdate, synchronize_session=False)
        s.commit()
    return render_template("editoraccion.html", accion=accion, email=email, name=given_name, user=user)


@app.route('/editorCampanyas/<int:campanya_id>', methods=["GET", "POST"])
def editorCamp(campanya_id):
    email = dict(session).get('email', None)
    given_name = dict(session).get('given_name', None)
    user = User.get_by_email(email)

    s = Session()
    query = s.query(Campanya)
    campanya = query.filter(Campanya.id == campanya_id).first()
    if request.method == 'POST':
        dictupdate = {Campanya.nombre: request.form['nombre'], Campanya.descripcion: request.form['descripcion']}
        query.filter(Campanya.id == campanya_id).update(dictupdate, synchronize_session=False)
        s.commit()
    return render_template("editorcamp.html", campanya=campanya, email=email, name=given_name,
                           user=user)

@app.route('/editorOferta/<int:offer_id>', methods=["GET", "POST"])
def editorOferta(offer_id):
    email = dict(session).get('email', None)
    given_name = dict(session).get('given_name', None)
    user = User.get_by_email(email)

    s = Session()
    query = s.query(Oferta)
    oferta = query.filter(Oferta.id == offer_id).first()
    if request.method == 'POST':
        dictupdate = {Oferta.nombre: request.form['nombre'], Oferta.descripcion: request.form['descripcion'], Oferta.precio: request.form['precio']}
        query.filter(Oferta.id == offer_id).update(dictupdate, synchronize_session=False)
        s.commit()
    return render_template("editoroferta.html", oferta=oferta, email=email, name=given_name,
                           user=user)

@app.route('/qr/<int:accion_id>')
def qr(accion_id):
    path = 'static/qr/acciones/' + str(accion_id) + ".png"
    return send_file(path, as_attachment=True)

@app.route('/qrOfertas/<int:offerId>')
def qrOfertas(offerId):
    path = 'static/qr/ofertas/' + str(offerId) + ".png"
    return send_file(path, as_attachment=True)


@app.route('/redeem/<int:accion_id>', methods=["GET", "POST"])
def redeem(accion_id):
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    session['accionId'] = accion_id
    return google.authorize_redirect(redirect_uri)

@app.route('/pay/<int:offer_id>', methods=["GET", "POST"])
def pay(offer_id):
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    session['offerId'] = offer_id
    return google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    try:
        tempLang = session['lang']
        session.clear()
        session['lang'] = tempLang
    except:
        pass
    return redirect('/')


@app.route('/campanyas')
def campanyas():
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    salary = get_balance(user.blockHash)
    campanyas = Campanya.getOrderedCampaigns()
    empresas = Campanya.getDistinctCompanies()
    try:
        del session['accionId']
        del session['offerId']
    except:
        pass
    return render_template('empresas.html', wallet=salary, email=email, name=given_name, w3=web3,
                           user=user, campanyas=campanyas, empresas=empresas)


@app.route('/campanyas/<emp>', methods=['GET', 'POST'])
def empresa(emp):
    email = dict(session).get('email', None)
    user = User.get_by_email(email)
    given_name = dict(session).get('given_name', None)
    salary = get_balance(user.blockHash)
    campanyas = Campanya.getCampaigns(emp)
    acciones = Accion.getActions(emp)
    return render_template('campanyas.html', wallet=salary, email=email, name=given_name, w3=web3,
                           user=user, campanyas=campanyas, empresa=emp, acciones=acciones)


@app.route('/registraraccion/<int:accion_id>', methods=['GET', 'POST'])
def registrarAccion(accion_id):
    user = User.get_by_email(session['email'])
    session['accionId'] = accion_id
    cReward = Accion.getActionById(accion_id)
    return render_template("subirimagen.html", name=session['name'], cReward=cReward, email=session['email'],
                           session=session, user=user, accionId=accion_id)


@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", code="500", type="Internal Server Error"), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code="403", type="Forbidden"), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", code="404", type="Not Found"), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code="400", type="Bad Request"), 400


@app.errorhandler(401)
def unauthorized(e):
    return render_template("error.html", code="401", type="Unauthorized"), 401


if __name__ == "__main__":
    app.run()
