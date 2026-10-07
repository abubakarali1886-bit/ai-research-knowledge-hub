from app.services.document_processor import DocumentProcessor


def test_metadata_supports_explicit_fields_and_inferred_topics():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Research Report\n"
        "Author: Ada Researcher, Ben Analyst\n"
        "Published: 2024\n"
        "Keywords: pass-through, prices\n"
        "The study examines inflation expectations and exchange rate transmission.",
        "report_2023.pdf",
    )

    assert metadata["author"] == "Ada Researcher, Ben Analyst"
    assert metadata["publication_year"] == 2024
    assert metadata["keywords"] == ["pass-through", "prices"]
    assert "Price Stability and Inflation" in metadata["topics"]
    assert "Exchange Rates and International Economics" in metadata["topics"]
    assert metadata["category"] == "Monetary Policy"


def test_filename_classifies_financial_stability_framework():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "BANK OF TANZANIA\nEmergency Liquidity Assistance Framework\nFinancial stability framework.",
        "Financial Stability - Emergency Liquidity Assistance Framework 2025.pdf",
    )

    assert metadata["category"] == "Financial Stability"
    assert metadata["document_type"] == "Framework"
    assert metadata["title"] == "Emergency Liquidity Assistance Framework"


def test_bot_public_notice_and_statistics_taxonomy():
    processor = DocumentProcessor()
    notice = processor.extract_content_metadata(
        "Government Securities Issuance Calendar 2025",
        "PUBLIC NOTICE Government Securities Issuance Calendar 2025.pdf",
    )
    statistics = processor.extract_content_metadata(
        "Payment systems statistics for mobile and card transactions.",
        "Payment Systems Statistics 2025.xlsx.pdf",
    )

    assert notice["document_type"] == "Public Notice"
    assert notice["category"] == "Financial Markets"
    assert "Government Finance and Securities" in notice["topics"]
    assert statistics["document_type"] == "Statistics Release"
    assert statistics["category"] == "Payment Systems"
    assert "Payment Systems" in statistics["topics"]


def test_file_validation_checks_size_and_content_type():
    processor = DocumentProcessor()

    assert processor.validate_file("paper.pdf", 100, "application/pdf")[0]
    assert not processor.validate_file("paper.pdf", 100, "text/plain")[0]
    assert not processor.validate_file("paper.pdf", processor.MAX_FILE_SIZE + 1, "application/pdf")[0]
    assert not processor.validate_file("paper.exe", 100, "application/octet-stream")[0]


def test_title_and_author_extraction_ignore_institutional_labels():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Exchange Rate Pass-Through to Inflation in Tanzania\n\nBy\nJohn A. Smith\nMary K. Example\n\nPrepared by:\nResearch Department\n\nDepartment: Monetary Policy",
        "Effects_of_Real_Exchange_Rate_Volatility_on_Tanzania_Exports.pdf",
    )

    assert metadata["title"] == "Effects of Real Exchange Rate Volatility on Tanzania's Exports"
    assert metadata["author"] == "John A. Smith, Mary K. Example"
    assert "Research Department" not in metadata["author"]


def test_newsletter_title_prefers_article_title_over_publication_name():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "Bank of Tanzania Research Newsletter\n"
        "Message from the Chairperson\n"
        "Emmanuel M. Tutuba\n"
        "Food Prices and Inflation in Tanzania\n"
        "C. Adam, D. Kwimbere, W. Mbowe and S. O'Connel",
        "Research Newsletter - 2013.pdf",
    )

    assert metadata["title"] == "Food Prices and Inflation in Tanzania"


def test_department_publication_title_ignores_cover_contact_block():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "For any enquiries contact:\n"
        "Secretariat to the National Council for Financial Inclusion\n"
        "Bank of Tanzania\n"
        "NATIONAL COUNCIL\n"
        "FOR FINANCIAL\n"
        "INCLUSION\n"
        "ANNUAL FINANCIAL INCLUSION REPORT 2023\n"
        "1ST EDITION",
        "Annual Reports - ANNUAL FINANCIAL INCLUSION REPORT 2023.pdf",
    )

    assert metadata["title"] == "ANNUAL FINANCIAL INCLUSION REPORT"


def test_financial_stability_cover_title_is_not_treated_as_generic_report():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "ISSN 1821 - 7761\n"
        "TANZANIA FINANCIAL STABILITY REPORT\n"
        "December 2025\n"
        "MOF URT BOT MOFP RGoZ\n"
        "PMO - RALG PMO-LER VPO - URT TIRA CMSA FCC TCRA DIB TCDC GBT FIU NPC",
        "document.pdf",
    )

    assert metadata["title"] == "TANZANIA FINANCIAL STABILITY REPORT"


def test_cover_title_wins_when_department_filename_only_has_series_and_year():
    processor = DocumentProcessor()
    metadata = processor.extract_content_metadata(
        "TANZANIA INVESTMENT REPORT 2023\nFOREIGN PRIVATE INVESTMENTS",
        "Tanzania Investment - 2023.pdf",
    )

    assert metadata["title"] == "TANZANIA INVESTMENT REPORT"
