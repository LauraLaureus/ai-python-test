from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import event

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args,
    pool_size=50,           # Max 50 connections
    max_overflow=200,       # +200 on demand
    pool_timeout=45,        # Wait 45s for the pool
    pool_pre_ping=True,     # Validate connections
    pool_recycle=3600,      # Recycle pool every hour
    )

@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL") # use WAL for journaling instead of writing directly into db
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA cache_size=-20000")
    cursor.execute("PRAGMA mmap_size=134217728;")
    cursor.execute("PRAGMA wal_autocheckpoint=2000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()

def create_db_and_tables(): # Create all the tables from the clases with the "table=True" param
    SQLModel.metadata.create_all(engine) 

def get_session(): # Handle for getting a DB Session
    with Session(engine) as session:
        yield session