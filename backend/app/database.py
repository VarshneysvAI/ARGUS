from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import uuid

SQLALCHEMY_DATABASE_URL = "sqlite:///./argus.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class ArgusSession(Base):
    __tablename__ = "argus_sessions"
    
    session_id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    trigger_type = Column(String(50), nullable=False) # 'LIVE_SIGNAL', 'CACHED_SCENARIO', 'MANUAL_PROMPT'
    incident_corridor = Column(String(100))
    raw_ingested_content = Column(Text, nullable=False)
    extracted_variables = Column(JSON, nullable=False)
    deterministic_state = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False)

class ArgusExtractedClaim(Base):
    __tablename__ = "argus_extracted_claims"
    
    claim_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("argus_sessions.session_id"))
    extracted_text = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    verification_status = Column(String(50), nullable=False)

class ArgusSignalEvent(Base):
    __tablename__ = "argus_signal_events"
    
    signal_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("argus_sessions.session_id"))
    signal_source = Column(String(50), nullable=False)
    t_signal = Column(DateTime(timezone=True), nullable=False)
    t_recommendation = Column(DateTime(timezone=True))
