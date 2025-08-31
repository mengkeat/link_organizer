"""
Database setup and session management for the link organizer.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, JSON, Table
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.ext.mutable import MutableList

# Define the base class for declarative models
Base = declarative_base()

# Association table for the many-to-many relationship between links and collections
link_collections = Table('link_collections', Base.metadata,
    Column('link_id', Integer, ForeignKey('link_data.id'), primary_key=True),
    Column('collection_id', Integer, ForeignKey('collections.id'), primary_key=True)
)

class ClassificationResult(Base):
    """Structured classification result"""
    __tablename__ = 'classification_results'

    id = Column(String, primary_key=True)
    link_data_id = Column(String, ForeignKey('link_data.id'), nullable=False)
    category = Column(String)
    subcategory = Column(String)
    tags = Column(MutableList.as_mutable(JSON))
    summary = Column(Text)
    confidence = Column(Float)
    content_type = Column(String)
    difficulty = Column(String)
    quality_score = Column(Integer)
    key_topics = Column(MutableList.as_mutable(JSON))
    target_audience = Column(String)

class LinkData(Base):
    """Represents a link and its associated data"""
    __tablename__ = 'link_data'

    id = Column(String, primary_key=True)
    link = Column(String, unique=True, nullable=False)
    filename = Column(String)
    status = Column(String, default="pending")
    content = Column(Text)
    screenshot_filename = Column(String)
    embedding = Column(JSON)  # For storing vector embeddings
    classification = relationship("ClassificationResult", uselist=False, back_populates="link_data")
    collections = relationship("Collection", secondary=link_collections, back_populates="links")

ClassificationResult.link_data = relationship("LinkData", back_populates="classification")

class Collection(Base):
    """Represents a smart collection of links"""
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    links = relationship("LinkData", secondary=link_collections, back_populates="collections")

# Create the database engine
engine = create_engine('sqlite:///links.db')

# Create all tables in the engine
Base.metadata.create_all(engine)

# Create a configured "Session" class
Session = sessionmaker(bind=engine)
