"""
Document Models for PostgreSQL Database
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.user import User

# Association table for many-to-many relationship between documents and keywords
document_keyword = Table(
    'document_keyword',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
    Column('keyword_id', Integer, ForeignKey('keywords.id', ondelete='CASCADE'), primary_key=True)
)

document_topic = Table(
    'document_topic',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
    Column('topic_id', Integer, ForeignKey('research_topics.id', ondelete='CASCADE'), primary_key=True)
)


class Document(Base):
    """Document model for storing research document metadata"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    authors_json = Column(Text, nullable=True)
    author_type = Column(String(30), default="unknown")
    author_confidence = Column(Float, nullable=True)
    author_source = Column(String(255), nullable=True)
    metadata_review_status = Column(String(30), default="needs_review")
    publication_year = Column(Integer, nullable=True)
    publication_period = Column(String(32), nullable=True)
    description = Column(Text, nullable=True)
    
    # File information
    file_path = Column(String(1000), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    file_type = Column(String(50), nullable=True)  # pdf, docx, etc.
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    
    # Metadata
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    document_type_id = Column(Integer, ForeignKey('document_types.id', ondelete='SET NULL'), nullable=True)
    
    # Chunk information
    chunk_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    uploader_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Relationships
    category = relationship("Category", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    keywords = relationship("Keyword", secondary=document_keyword, back_populates="documents")
    topics = relationship("ResearchTopic", secondary=document_topic, back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploader_id])
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}')>"


class Category(Base):
    """Category/Department model"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    documents = relationship("Document", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class DocumentType(Base):
    """Document Type model (e.g., Report, Working Paper, Policy Brief)"""
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    documents = relationship("Document", back_populates="document_type")
    
    def __repr__(self):
        return f"<DocumentType(id={self.id}, name='{self.name}')>"


class Keyword(Base):
    """Keyword model for document tagging"""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    documents = relationship("Document", secondary=document_keyword, back_populates="keywords")
    
    def __repr__(self):
        return f"<Keyword(id={self.id}, name='{self.name}')>"


class ResearchTopic(Base):
    """Controlled research topics, kept separate from document keywords."""
    __tablename__ = "research_topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", secondary=document_topic, back_populates="topics")


class DocumentChunk(Base):
    """Store reference to document chunks stored in ChromaDB"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    chunk_text = Column(Text, nullable=False)  # Store chunk text for reference
    chunk_length = Column(Integer, nullable=True)  # Number of characters
    
    # ChromaDB reference
    chroma_id = Column(String(100), nullable=True)  # ID in ChromaDB
    
    # Metadata for source citation
    page_number = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"