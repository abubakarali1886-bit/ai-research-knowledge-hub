from app.services.document_processor import DocumentProcessor


def test_embedded_or_incidental_person_is_not_an_author():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Bank of Tanzania Research Newsletter\n"
        "Message from the Chairperson\n"
        "Emmanuel M. Tutuba\n"
        "Food Prices and Inflation in Tanzania\n"
        "C. Adam, D. Kwimbere, W. Mbowe and S. O'Connel",
        "Research Newsletter - 2013.pdf",
    )

    assert metadata["author"] == "Bank of Tanzania"
    assert metadata["author_type"] == "institutional"
    assert metadata["author_confidence"] >= 0.9


def test_explicit_multiple_authors_are_preserved():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Title: Monetary Policy Study\n"
        "Authors: Jane Doe, John Smith and Amina Ali\n"
        "Published: 2024",
        "working-paper.pdf",
    )

    assert metadata["authors"] == ["Jane Doe", "John Smith", "Amina Ali"]
    assert metadata["author_type"] == "individual"
    assert metadata["author_source"] == "explicit author label"


def test_working_paper_cover_authors_are_preserved():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Bank of Tanzania WP No. 40: 2025\n"
        "Effects of Real Exchange Rate Volatility on Tanzania's Exports\n"
        "Wilfred E. Mbowe Hossana P. Mpango\n"
        "Working Paper Series",
        "Working Papers Series - Effects of Real Exchange Rate Volatility on Tanzania's Exports.pdf",
    )

    assert metadata["authors"] == ["Wilfred E. Mbowe", "Hossana P. Mpango"]
    assert metadata["author_type"] == "individual"


def test_bot_document_without_individual_author_is_institutional():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Bank of Tanzania\nAnnual publication\nHistorical references 2013 and 2020",
        "annual-report.pdf",
    )

    assert metadata["author"] == "Bank of Tanzania"
    assert metadata["author_type"] == "institutional"
    assert metadata["author_confidence"] >= 0.9
