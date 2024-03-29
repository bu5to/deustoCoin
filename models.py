from sqlalchemy import Column, String, Integer, ForeignKey, Float, or_, desc
from sqlalchemy.orm import relationship, backref
from base import Base, Session
import datetime


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    blockHash = Column(String(128), nullable=True)
    pk = Column(String(128), nullable=True)
    picture = Column(String(128), nullable=True)
    role = Column(String(128), nullable=False)
    organizacion = Column(String(128), nullable=False)

    def __init__(self, name, email, blockHash, pk, picture, role, organizacion):
        self.name = name
        self.email = email
        self.blockHash = blockHash
        self.pk = pk
        self.picture = picture
        self.role = role
        self.organizacion = organizacion

    def __repr__(self):
        return f'<User {self.email}>'

    def save(self):
        s = Session()
        if not self.id:
            s.add(self)
        s.commit()
        s.expunge(self)
        s.close()

    @staticmethod
    def getCompanyBlockAddr(compName):
        s = Session()
        query = s.query(User)
        return query.filter(User.organizacion == compName).first()

    @staticmethod
    def get_by_email(email):
        s = Session()
        query = s.query(User)
        return query.filter(User.email == email).first()

    @staticmethod
    def get_by_blockAddr(blockHash):
        s = Session()
        query = s.query(User)
        return query.filter(User.blockHash == blockHash).first()


class Transaccion(Base):
    __tablename__ = 'transaccion'
    id = Column(Integer, primary_key=True)
    fecha = Column(String(80), nullable=False)
    transHash = Column(String(255), nullable=False)
    remitente = Column(String(255), nullable=False)
    destinatario = Column(String(255), nullable=False)
    campanya = Column(Integer, ForeignKey('campanya.id'),
                      nullable=True)
    cantidad = Column(Float, nullable=False)
    imgHash = Column(String(255), nullable=True)
    proof = Column(String(255), nullable=True)

    def __init__(self, fecha, transHash, remitente, destinatario, campanya, cantidad, imgHash, proof):
        self.fecha = fecha
        self.transHash = transHash
        self.remitente = remitente
        self.destinatario = destinatario
        self.campanya = campanya
        self.cantidad = cantidad
        self.imgHash = imgHash
        self.proof = proof

    def __repr__(self):
        return f'<Transaccion {self.transHash}>'

    def save(self):
        s = Session()
        if not self.id:
            s.add(self)
        s.commit()
        s.expunge(self)
        s.close()

    @staticmethod
    def getTransactions(email):
        s = Session()
        query = s.query(Transaccion).order_by(Transaccion.id)
        return query.filter(or_(Transaccion.remitente == email, Transaccion.destinatario == email)).all()

    @staticmethod
    def getAllTransactions():
        s = Session()
        query = s.query(Transaccion).order_by(Transaccion.id)
        return query.all()


class KPIporFechas(Base):
    __tablename__ = 'kpi_fechas'
    id = Column(Integer, primary_key=True)
    accion = Column(Integer, ForeignKey('accion.id', ondelete='CASCADE'))
    fecha = Column(String, nullable=False)
    kpi = Column(Integer)

    def __init__(self, fecha, accion, kpi):
        self.fecha = fecha
        self.accion = accion
        self.kpi = kpi

    @staticmethod
    def getAllKPIs():
        s = Session()
        query = s.query(KPIporFechas)
        return query.all()

    @staticmethod
    def getGraphData(id):
        s = Session()
        query = s.query(KPIporFechas)
        results = query.filter(KPIporFechas.accion == id).order_by(desc(KPIporFechas.id)).all()
        query2 = s.query(Accion)
        name = query2.filter(Accion.id == id).first().nombre
        data = {
            "name": name,
            "results": results
        }
        return data

    @staticmethod
    def saveTodaysKPI():
        fechas = []
        acciones = Accion.getAllActions()
        kpis = KPIporFechas.getAllKPIs()
        if len(kpis) > 0:
            for k in kpis:
                fechas.append(k.fecha)
        dt = datetime.datetime.today()
        today = dt.strftime("%d/%m/%Y")
        if today not in fechas:
            s = Session()
            fechas.append(today)
            for a in acciones:
                kpi = KPIporFechas(today, a.id, a.kpi)
                s.add(kpi)
            s.commit()
            s.close()
        else:
            pass


class Accion(Base):
    __tablename__ = 'accion'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    empresa = Column(String(255), nullable=False)
    descripcion = Column(String, unique=True, nullable=False)
    recompensa = Column(Float, nullable=False)
    indicadorKpi = Column(String, nullable=False)
    campanya_id = Column(Integer, ForeignKey('campanya.id'))
    kpi = Column(Integer, default=0)
    kpiObj = Column(Integer, default=0)
    kpis = relationship(KPIporFechas, backref=backref("kpi_fechas", passive_deletes=True))

    def __init__(self, nombre, empresa, descripcion, recompensa, indicadorKpi, kpiObj, campanya_id):
        self.nombre = nombre
        self.empresa = empresa
        self.descripcion = descripcion
        self.recompensa = recompensa
        self.indicadorKpi = indicadorKpi
        self.kpiObj = kpiObj
        self.campanya_id = campanya_id

    def __repr__(self):
        return f'<Acción {self.nombre}>: {self.descripcion}'

    def save(self):
        s = Session()
        if not self.id:
            s.add(self)
        s.commit()
        s.expunge(self)
        s.close()

    @staticmethod
    def getActions(empresa):
        s = Session()
        query = s.query(Accion)
        return query.filter(Accion.empresa == empresa).all()

    @staticmethod
    def getActionsOfCampaign(campanya_id):
        s = Session()
        query = s.query(Accion)
        return query.filter(Accion.campanya_id == campanya_id).all()

    @staticmethod
    def getAllActions():
        s = Session()
        query = s.query(Accion)
        return query.all()

    @staticmethod
    def getIdByName(nombre):
        s = Session()
        query = s.query(Accion)
        return query.filter(Accion.nombre == nombre).first().id

    @staticmethod
    def getActionById(id):
        s = Session()
        query = s.query(Accion)
        return query.filter(Accion.id == id).first()


class Campanya(Base):
    __tablename__ = 'campanya'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    empresa = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    acciones = relationship("Accion")

    def __init__(self, nombre, empresa, descripcion):
        self.nombre = nombre
        self.empresa = empresa
        self.descripcion = descripcion

    @staticmethod
    def getCampaigns(empresa):
        s = Session()
        query = s.query(Campanya)
        return query.filter(Campanya.empresa == empresa).all()

    @staticmethod
    def getAllCampaigns():
        s = Session()
        query = s.query(Campanya)
        return query.all()

    @staticmethod
    def getOrderedCampaigns():
        s = Session()
        query = s.query(Campanya)
        query = query.order_by(Campanya.empresa).all()
        return query

    @staticmethod
    def getDistinctCompanies():
        s = Session()
        query = s.query(Campanya)
        query = query.distinct(Campanya.empresa).all()
        companies = []
        for campaign in query:
            companies.append(campaign.empresa)
        return companies

    @staticmethod
    def getIdByName(nombre):
        s = Session()
        query = s.query(Campanya)
        return query.filter(Campanya.nombre == nombre).first()

    @staticmethod
    def getCampaignById(id):
        s = Session()
        query = s.query(Campanya)
        return query.filter(Campanya.id == id).first()


class Oferta(Base):
    __tablename__ = 'oferta'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    empresa = Column(String(80), nullable=False)
    descripcion = Column(String, nullable=True)
    precio = Column(String, nullable=False)

    def __init__(self, nombre, empresa, descripcion, precio):
        self.nombre = nombre
        self.empresa = empresa
        self.descripcion = descripcion
        self.precio = precio

    @staticmethod
    def getOffers(empresa):
        s = Session()
        query = s.query(Oferta)
        return query.filter(Oferta.empresa == empresa).all()

    @staticmethod
    def getAllOffers():
        s = Session()
        query = s.query(Oferta)
        return query.all()

    @staticmethod
    def getIdByName(nombre):
        s = Session()
        query = s.query(Oferta)
        return query.filter(Oferta.nombre == nombre).first().id

    @staticmethod
    def getOfferById(id):
        s = Session()
        query = s.query(Oferta)
        return query.filter(Oferta.id == id).first()
