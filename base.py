from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask.cli import with_appcontext
import os

engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)

Base = declarative_base()
Base.metadata.create_all(engine)

@click.command()
@with_appcontext
def init_db():
    Base.metadata.create_all(bind=engine)
