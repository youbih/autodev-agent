from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# SQLite database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./my_user_service.db"

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=True  # Set to False in production
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    """
    Dependency function to get database session.
    Usage in FastAPI endpoints:
    
    @app.get("/users/{id}")
    def read_user(id: int, db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables
def create_tables():
    """Create all database tables"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)