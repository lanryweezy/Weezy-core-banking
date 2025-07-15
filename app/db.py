from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables in the database
# This is useful for initial setup or testing without migrations
def create_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    # This will create the tables if you run this file directly
    # In a real application, you'd likely use Alembic for migrations
    print(f"Creating database tables for URI: {Config.SQLALCHEMY_DATABASE_URI}")
    create_tables()
    print("Tables created (if they didn't exist).")
