import asyncio
import sys
import types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.documents import delete_document
from app.db.database import Base
from app.models.document import Document, DocumentChunk
from app.models.saved_research import SavedResearch
from app.models.user import User, UserRole


def test_delete_document_removes_record_chunks_saved_state_and_file(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    researcher = User(username="researcher", email="researcher@example.com", password_hash="unused", role=UserRole.RESEARCHER, is_active=True, is_verified=True)
    document_file = tmp_path / "research.pdf"
    document_file.write_bytes(b"pdf")
    document = Document(title="Research report", file_path=str(document_file), file_name="research.pdf", is_active=True)
    db.add_all([researcher, document])
    db.commit()
    chunk = DocumentChunk(document_id=document.id, chunk_index=0, chunk_text="research text")
    saved = SavedResearch(user_id=researcher.id, document_id=document.id)
    db.add_all([chunk, saved])
    db.commit()
    document_id = document.id
    deleted_vector_ids = []

    class FakeVectorStore:
        def delete_document_chunks(self, document_id, collection_name="research_documents"):
            deleted_vector_ids.append(document_id)

    monkeypatch.setitem(sys.modules, "app.services.vector_store", types.SimpleNamespace(VectorStore=FakeVectorStore))

    result = asyncio.run(delete_document(document_id=document_id, db=db, current_user=researcher))

    assert result["message"] == "Document deleted successfully"
    assert db.query(Document).filter(Document.id == document_id).first() is None
    assert db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count() == 0
    assert db.query(SavedResearch).filter(SavedResearch.document_id == document_id).count() == 0
    assert not document_file.exists()
    assert deleted_vector_ids == [document_id]
    db.close()
    engine.dispose()
