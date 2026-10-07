import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.documents import DocumentMetadataUpdate, update_document_metadata
from app.db.database import Base
from app.models.document import Document
from app.models.user import User, UserRole


def test_document_metadata_edit_persists_manually_entered_author():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    researcher = User(username="researcher", email="researcher@example.com", password_hash="unused", role=UserRole.RESEARCHER, is_active=True, is_verified=True)
    document = Document(title="Untitled report", file_path="/tmp/report.pdf", file_name="report.pdf", author=None, is_active=True)
    db.add_all([researcher, document])
    db.commit()

    result = asyncio.run(update_document_metadata(
        document_id=document.id,
        metadata=DocumentMetadataUpdate(title="Policy report", author="Amina Mushi", publication_year=2025),
        db=db,
        current_user=researcher,
    ))

    db.refresh(document)
    assert document.author == "Amina Mushi"
    assert document.authors_json == '["Amina Mushi"]'
    assert document.author_source == "Manually entered"
    assert document.metadata_review_status == "reviewed"
    assert document.publication_year == 2025
    assert result["author"] == "Amina Mushi"
    db.close()
    engine.dispose()
