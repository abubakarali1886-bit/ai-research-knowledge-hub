"""
Seed database with initial data
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document import Category, DocumentType, Keyword
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_categories(db: Session):
    """Seed categories"""
    categories = [
        {"name": "Monetary Policy", "description": "Research on monetary policy frameworks and implementation"},
        {"name": "Financial Stability", "description": "Research on financial system stability and risks"},
        {"name": "Macroeconomics", "description": "Research on macroeconomic trends and analysis"},
        {"name": "Banking Supervision", "description": "Research on banking regulation and supervision"},
        {"name": "Payment Systems", "description": "Research on payment and settlement systems"},
        {"name": "Financial Markets", "description": "Foreign exchange, reserves, government securities and market infrastructure"},
        {"name": "Financial Deepening and Inclusion", "description": "Financial inclusion, consumer protection, fintech and financial deepening"},
        {"name": "Currency and Banking Services", "description": "Currency issuance, banknotes, coins and banking services"},
        {"name": "Economic Research", "description": "General economic research and analysis"},
    ]
    
    for cat_data in categories:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            category = Category(**cat_data)
            db.add(category)
            logger.info(f"Added category: {cat_data['name']}")
    
    db.commit()


def seed_document_types(db: Session):
    """Seed document types"""
    doc_types = [
        {"name": "Working Paper", "description": "Preliminary research findings"},
        {"name": "Policy Brief", "description": "Concise policy recommendations"},
        {"name": "Research Report", "description": "Comprehensive research findings"},
        {"name": "Staff Note", "description": "Internal staff analysis"},
        {"name": "Annual Report", "description": "Annual organizational report"},
        {"name": "Technical Report", "description": "Detailed technical analysis"},
        {"name": "Public Notice", "description": "Official public notices and public information"},
        {"name": "Press Release", "description": "Official press releases and statements"},
        {"name": "Statement", "description": "Official statements and communiques"},
        {"name": "Circular", "description": "Institutional circulars"},
        {"name": "Regulation", "description": "Acts, regulations and regulatory instruments"},
        {"name": "Guideline", "description": "Guidelines and guidance notes"},
        {"name": "Procedure", "description": "Procedures and operational instructions"},
        {"name": "Rule", "description": "Rules and market conduct rules"},
        {"name": "Agreement", "description": "Institutional agreements"},
        {"name": "Code of Conduct", "description": "Codes of conduct"},
        {"name": "Statistical Bulletin", "description": "Economic and financial statistical releases"},
        {"name": "Statistics Release", "description": "Economic, financial and payment statistics releases"},
        {"name": "Survey", "description": "Institutional surveys"},
        {"name": "Calendar", "description": "Issuance and meeting calendars"},
        {"name": "Tender", "description": "Tenders and auction notices"},
        {"name": "Form", "description": "Forms and application documents"},
        {"name": "Newsletter", "description": "Newsletters and institutional journals"},
        {"name": "Weekly Financial Markets Report", "description": "Weekly financial markets publications"},
    ]
    
    for dt_data in doc_types:
        existing = db.query(DocumentType).filter(DocumentType.name == dt_data["name"]).first()
        if not existing:
            doc_type = DocumentType(**dt_data)
            db.add(doc_type)
            logger.info(f"Added document type: {dt_data['name']}")
    
    db.commit()


def seed_keywords(db: Session):
    """Seed common keywords"""
    keywords = [
        "Inflation", "GDP Growth", "Monetary Policy", "Interest Rates",
        "Financial Stability", "Bank Regulation", "Payment Systems",
        "Economic Growth", "Exchange Rates", "Fiscal Policy",
        "Unemployment", "Productivity", "Trade", "Investment",
        "Banking", "Digital Currency", "CBDC", "Fintech"
    ]
    
    for kw_data in keywords:
        existing = db.query(Keyword).filter(Keyword.name == kw_data).first()
        if not existing:
            keyword = Keyword(name=kw_data)
            db.add(keyword)
            logger.info(f"Added keyword: {kw_data}")
    
    db.commit()


def seed_all():
    """Seed all data"""
    logger.info("Starting database seeding...")
    
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_document_types(db)
        seed_keywords(db)
        logger.info("Database seeding completed successfully!")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()