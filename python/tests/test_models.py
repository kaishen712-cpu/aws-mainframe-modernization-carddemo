"""
Unit tests for all CardDemo dataclass models.

Covers construction, default values, and field types for every record
type, the commarea, export records, and report structures.
"""

from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    DailyTransactionRecord,
    DisclosureGroupRecord,
    TranCatBalRecord,
    TransactionCategoryRecord,
    TransactionIndexRecord,
    TransactionRecord,
    TransactionTypeRecord,
    UserSecurityRecord,
)
from python.models.commarea import CardDemoCommarea
from python.models.export_record import (
    ExportAccountData,
    ExportCardData,
    ExportCardXrefData,
    ExportCustomerData,
    ExportRecord,
    ExportTransactionData,
    EXPORT_REC_TYPE_CUSTOMER,
    EXPORT_REC_TYPE_ACCOUNT,
    EXPORT_REC_TYPE_TRANSACTION,
    EXPORT_REC_TYPE_CARD_XREF,
    EXPORT_REC_TYPE_CARD,
)
from python.models.report import (
    ReportNameHeader,
    TransactionDetailReport,
    ReportPageTotals,
    ReportAccountTotals,
    ReportGrandTotals,
    TRANSACTION_HEADER_1,
    TRANSACTION_HEADER_2,
)


# ===================================================================
# AccountRecord
# ===================================================================

class TestAccountRecord:
    """Tests for AccountRecord (CVACT01Y.cpy)."""

    def test_defaults(self) -> None:
        rec = AccountRecord()
        assert rec.acct_id == ""
        assert rec.acct_active_status == ""
        assert rec.acct_curr_bal == 0.0
        assert rec.acct_credit_limit == 0.0
        assert rec.acct_cash_credit_limit == 0.0
        assert rec.acct_open_date == ""
        assert rec.acct_expiration_date == ""
        assert rec.acct_reissue_date == ""
        assert rec.acct_curr_cyc_credit == 0.0
        assert rec.acct_curr_cyc_debit == 0.0
        assert rec.acct_addr_zip == ""
        assert rec.acct_group_id == ""

    def test_construction(self) -> None:
        rec = AccountRecord(
            acct_id="00000000001",
            acct_active_status="Y",
            acct_curr_bal=1500.50,
            acct_credit_limit=5000.00,
            acct_cash_credit_limit=1000.00,
            acct_open_date="2020-01-15",
            acct_expiration_date="2025-01-15",
            acct_reissue_date="2023-01-15",
            acct_curr_cyc_credit=200.00,
            acct_curr_cyc_debit=100.00,
            acct_addr_zip="10001",
            acct_group_id="GRP001",
        )
        assert rec.acct_id == "00000000001"
        assert rec.acct_active_status == "Y"
        assert rec.acct_curr_bal == 1500.50
        assert rec.acct_credit_limit == 5000.00

    def test_field_types(self) -> None:
        rec = AccountRecord(acct_curr_bal=100.0)
        assert isinstance(rec.acct_curr_bal, float)
        assert isinstance(rec.acct_id, str)


# ===================================================================
# CardRecord
# ===================================================================

class TestCardRecord:
    """Tests for CardRecord (CVACT02Y.cpy)."""

    def test_defaults(self) -> None:
        rec = CardRecord()
        assert rec.card_num == ""
        assert rec.card_acct_id == ""
        assert rec.card_cvv_cd == ""
        assert rec.card_embossed_name == ""
        assert rec.card_expiration_date == ""
        assert rec.card_active_status == ""

    def test_construction(self) -> None:
        rec = CardRecord(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="JOHN DOE",
            card_expiration_date="2025-12-31",
            card_active_status="Y",
        )
        assert rec.card_num == "4111111111111111"
        assert rec.card_cvv_cd == "123"


# ===================================================================
# CardXrefRecord
# ===================================================================

class TestCardXrefRecord:
    """Tests for CardXrefRecord (CVACT03Y.cpy)."""

    def test_defaults(self) -> None:
        rec = CardXrefRecord()
        assert rec.xref_card_num == ""
        assert rec.xref_cust_id == ""
        assert rec.xref_acct_id == ""

    def test_construction(self) -> None:
        rec = CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )
        assert rec.xref_card_num == "4111111111111111"
        assert rec.xref_cust_id == "000000001"
        assert rec.xref_acct_id == "00000000001"


# ===================================================================
# CustomerRecord
# ===================================================================

class TestCustomerRecord:
    """Tests for CustomerRecord (CVCUS01Y.cpy)."""

    def test_defaults(self) -> None:
        rec = CustomerRecord()
        assert rec.cust_id == ""
        assert rec.cust_first_name == ""
        assert rec.cust_last_name == ""
        assert rec.cust_ssn == ""
        assert rec.cust_fico_credit_score == ""

    def test_construction(self) -> None:
        rec = CustomerRecord(
            cust_id="000000001",
            cust_first_name="Jane",
            cust_middle_name="M",
            cust_last_name="Smith",
            cust_addr_state_cd="NY",
            cust_addr_country_cd="USA",
            cust_addr_zip="10001",
            cust_ssn="123456789",
            cust_dob_yyyy_mm_dd="1990-05-15",
            cust_fico_credit_score="750",
        )
        assert rec.cust_first_name == "Jane"
        assert rec.cust_addr_state_cd == "NY"
        assert rec.cust_fico_credit_score == "750"

    def test_all_18_fields(self) -> None:
        rec = CustomerRecord()
        field_count = len(rec.__dataclass_fields__)
        assert field_count == 18


# ===================================================================
# TransactionRecord
# ===================================================================

class TestTransactionRecord:
    """Tests for TransactionRecord (CVTRA05Y.cpy)."""

    def test_defaults(self) -> None:
        rec = TransactionRecord()
        assert rec.tran_id == ""
        assert rec.tran_amt == 0.0
        assert rec.tran_card_num == ""

    def test_construction(self) -> None:
        rec = TransactionRecord(
            tran_id="0000000000000001",
            tran_type_cd="SA",
            tran_cat_cd="5001",
            tran_source="ONLINE",
            tran_desc="Coffee purchase",
            tran_amt=4.50,
            tran_merchant_id="000000001",
            tran_merchant_name="Starbucks",
            tran_card_num="4111111111111111",
        )
        assert rec.tran_amt == 4.50
        assert rec.tran_type_cd == "SA"

    def test_field_count(self) -> None:
        assert len(TransactionRecord.__dataclass_fields__) == 13


# ===================================================================
# DailyTransactionRecord
# ===================================================================

class TestDailyTransactionRecord:
    """Tests for DailyTransactionRecord (CVTRA06Y.cpy)."""

    def test_defaults(self) -> None:
        rec = DailyTransactionRecord()
        assert rec.dalytran_id == ""
        assert rec.dalytran_amt == 0.0

    def test_construction(self) -> None:
        rec = DailyTransactionRecord(
            dalytran_id="0000000000000001",
            dalytran_type_cd="SA",
            dalytran_amt=99.99,
        )
        assert rec.dalytran_type_cd == "SA"
        assert rec.dalytran_amt == 99.99

    def test_field_count_matches_transaction(self) -> None:
        assert (
            len(DailyTransactionRecord.__dataclass_fields__)
            == len(TransactionRecord.__dataclass_fields__)
        )


# ===================================================================
# TranCatBalRecord
# ===================================================================

class TestTranCatBalRecord:
    """Tests for TranCatBalRecord (CVTRA01Y.cpy)."""

    def test_defaults(self) -> None:
        rec = TranCatBalRecord()
        assert rec.trancat_acct_id == ""
        assert rec.tran_cat_bal == 0.0

    def test_construction(self) -> None:
        rec = TranCatBalRecord(
            trancat_acct_id="00000000001",
            trancat_type_cd="SA",
            trancat_cd="5001",
            tran_cat_bal=250.75,
        )
        assert rec.tran_cat_bal == 250.75


# ===================================================================
# DisclosureGroupRecord
# ===================================================================

class TestDisclosureGroupRecord:
    """Tests for DisclosureGroupRecord (CVTRA02Y.cpy)."""

    def test_defaults(self) -> None:
        rec = DisclosureGroupRecord()
        assert rec.dis_acct_group_id == ""
        assert rec.dis_int_rate == 0.0

    def test_construction(self) -> None:
        rec = DisclosureGroupRecord(
            dis_acct_group_id="GRP001",
            dis_tran_type_cd="SA",
            dis_tran_cat_cd="5001",
            dis_int_rate=18.99,
        )
        assert rec.dis_int_rate == 18.99


# ===================================================================
# TransactionTypeRecord
# ===================================================================

class TestTransactionTypeRecord:
    """Tests for TransactionTypeRecord (CVTRA03Y.cpy)."""

    def test_defaults(self) -> None:
        rec = TransactionTypeRecord()
        assert rec.tran_type == ""
        assert rec.tran_type_desc == ""

    def test_construction(self) -> None:
        rec = TransactionTypeRecord(tran_type="SA", tran_type_desc="Sale")
        assert rec.tran_type == "SA"
        assert rec.tran_type_desc == "Sale"


# ===================================================================
# TransactionCategoryRecord
# ===================================================================

class TestTransactionCategoryRecord:
    """Tests for TransactionCategoryRecord (CVTRA04Y.cpy)."""

    def test_defaults(self) -> None:
        rec = TransactionCategoryRecord()
        assert rec.tran_type_cd == ""
        assert rec.tran_cat_cd == ""
        assert rec.tran_cat_type_desc == ""

    def test_construction(self) -> None:
        rec = TransactionCategoryRecord(
            tran_type_cd="SA",
            tran_cat_cd="5001",
            tran_cat_type_desc="Retail Sale",
        )
        assert rec.tran_cat_type_desc == "Retail Sale"


# ===================================================================
# UserSecurityRecord
# ===================================================================

class TestUserSecurityRecord:
    """Tests for UserSecurityRecord (CSUSR01Y.cpy)."""

    def test_defaults(self) -> None:
        rec = UserSecurityRecord()
        assert rec.sec_usr_id == ""
        assert rec.sec_usr_type == ""

    def test_construction(self) -> None:
        rec = UserSecurityRecord(
            sec_usr_id="ADMIN001",
            sec_usr_fname="Admin",
            sec_usr_lname="User",
            sec_usr_pwd="pass1234",
            sec_usr_type="A",
        )
        assert rec.sec_usr_id == "ADMIN001"
        assert rec.sec_usr_type == "A"


# ===================================================================
# TransactionIndexRecord
# ===================================================================

class TestTransactionIndexRecord:
    """Tests for TransactionIndexRecord (COSTM01.CPY)."""

    def test_defaults(self) -> None:
        rec = TransactionIndexRecord()
        assert rec.trnx_card_num == ""
        assert rec.trnx_id == ""
        assert rec.trnx_amt == 0.0

    def test_construction(self) -> None:
        rec = TransactionIndexRecord(
            trnx_card_num="4111111111111111",
            trnx_id="0000000000000001",
            trnx_type_cd="SA",
            trnx_amt=50.00,
        )
        assert rec.trnx_card_num == "4111111111111111"
        assert rec.trnx_amt == 50.00


# ===================================================================
# CardDemoCommarea
# ===================================================================

class TestCardDemoCommarea:
    """Tests for CardDemoCommarea (COCOM01Y.cpy)."""

    def test_defaults(self) -> None:
        ca = CardDemoCommarea()
        assert ca.cdemo_from_tranid == ""
        assert ca.cdemo_user_id == ""
        assert ca.cdemo_pgm_context == 0

    def test_construction(self) -> None:
        ca = CardDemoCommarea(
            cdemo_from_tranid="CC00",
            cdemo_to_program="COSGN00C",
            cdemo_user_id="ADMIN001",
            cdemo_user_type="A",
            cdemo_pgm_context=1,
            cdemo_cust_id="000000001",
            cdemo_acct_id="00000000001",
            cdemo_card_num="4111111111111111",
            cdemo_last_map="COSGN0A",
            cdemo_last_mapset="COSGN00",
        )
        assert ca.cdemo_user_id == "ADMIN001"
        assert ca.cdemo_card_num == "4111111111111111"

    def test_is_admin(self) -> None:
        ca = CardDemoCommarea(cdemo_user_type="A")
        assert ca.is_admin is True
        assert ca.is_user is False

    def test_is_user(self) -> None:
        ca = CardDemoCommarea(cdemo_user_type="U")
        assert ca.is_admin is False
        assert ca.is_user is True

    def test_program_context(self) -> None:
        ca = CardDemoCommarea(cdemo_pgm_context=0)
        assert ca.is_program_enter is True
        assert ca.is_program_reenter is False
        ca.cdemo_pgm_context = 1
        assert ca.is_program_enter is False
        assert ca.is_program_reenter is True


# ===================================================================
# Export Records
# ===================================================================

class TestExportRecord:
    """Tests for ExportRecord and sub-record variants (CVEXPORT.cpy)."""

    def test_defaults(self) -> None:
        rec = ExportRecord()
        assert rec.export_rec_type == ""
        assert rec.record_data is None

    def test_customer_variant(self) -> None:
        cust = ExportCustomerData(exp_cust_id=1, exp_cust_first_name="John")
        rec = ExportRecord(
            export_rec_type=EXPORT_REC_TYPE_CUSTOMER,
            export_timestamp="2024-03-15 10:30:00.000000",
            record_data=cust,
        )
        assert rec.export_rec_type == "C"
        assert isinstance(rec.record_data, ExportCustomerData)
        assert rec.record_data.exp_cust_first_name == "John"

    def test_account_variant(self) -> None:
        acct = ExportAccountData(exp_acct_id="00000000001", exp_acct_curr_bal=1000.0)
        rec = ExportRecord(
            export_rec_type=EXPORT_REC_TYPE_ACCOUNT,
            record_data=acct,
        )
        assert rec.export_rec_type == "A"
        assert isinstance(rec.record_data, ExportAccountData)

    def test_transaction_variant(self) -> None:
        txn = ExportTransactionData(exp_tran_id="0000000000000001", exp_tran_amt=50.0)
        rec = ExportRecord(
            export_rec_type=EXPORT_REC_TYPE_TRANSACTION,
            record_data=txn,
        )
        assert rec.export_rec_type == "T"

    def test_card_xref_variant(self) -> None:
        xref = ExportCardXrefData(exp_xref_card_num="4111111111111111")
        rec = ExportRecord(
            export_rec_type=EXPORT_REC_TYPE_CARD_XREF,
            record_data=xref,
        )
        assert rec.export_rec_type == "X"

    def test_card_variant(self) -> None:
        card = ExportCardData(exp_card_num="4111111111111111", exp_card_cvv_cd=123)
        rec = ExportRecord(
            export_rec_type=EXPORT_REC_TYPE_CARD,
            record_data=card,
        )
        assert rec.export_rec_type == "D"

    def test_export_date_and_time(self) -> None:
        rec = ExportRecord(export_timestamp="2024-03-15 10:30:00.000000")
        assert rec.export_date == "2024-03-15"
        assert rec.export_time == "10:30:00.000000"

    def test_export_date_empty(self) -> None:
        rec = ExportRecord(export_timestamp="")
        assert rec.export_date == ""
        assert rec.export_time == ""

    def test_customer_data_defaults(self) -> None:
        cust = ExportCustomerData()
        assert cust.exp_cust_id == 0
        assert cust.exp_cust_addr_lines == ["", "", ""]
        assert cust.exp_cust_phone_nums == ["", ""]

    def test_record_type_constants(self) -> None:
        assert EXPORT_REC_TYPE_CUSTOMER == "C"
        assert EXPORT_REC_TYPE_ACCOUNT == "A"
        assert EXPORT_REC_TYPE_TRANSACTION == "T"
        assert EXPORT_REC_TYPE_CARD_XREF == "X"
        assert EXPORT_REC_TYPE_CARD == "D"


# ===================================================================
# Report Structures
# ===================================================================

class TestReportStructures:
    """Tests for report formatting structures (CVTRA07Y.cpy)."""

    def test_report_name_header_defaults(self) -> None:
        hdr = ReportNameHeader()
        assert hdr.rept_short_name == "DALYREPT"
        assert hdr.rept_long_name == "Daily Transaction Report"

    def test_report_name_header_format(self) -> None:
        hdr = ReportNameHeader(
            rept_start_date="2024-01-01",
            rept_end_date="2024-01-31",
        )
        line = hdr.format_header()
        assert "DALYREPT" in line
        assert "Daily Transaction Report" in line
        assert "2024-01-01" in line
        assert "2024-01-31" in line

    def test_transaction_headers(self) -> None:
        assert "Transaction ID" in TRANSACTION_HEADER_1
        assert "Account ID" in TRANSACTION_HEADER_1
        assert len(TRANSACTION_HEADER_2) == 133

    def test_detail_line(self) -> None:
        detail = TransactionDetailReport(
            tran_report_trans_id="0000000000000001",
            tran_report_account_id="00000000001",
            tran_report_type_cd="SA",
            tran_report_type_desc="Sale",
            tran_report_cat_cd="5001",
            tran_report_cat_desc="Retail",
            tran_report_source="ONLINE",
            tran_report_amt=123.45,
        )
        line = detail.format_line()
        assert "0000000000000001" in line
        assert "00000000001" in line
        assert "123.45" in line

    def test_page_totals(self) -> None:
        pt = ReportPageTotals(rept_page_total=1234.56)
        line = pt.format_line()
        assert "Page Total" in line
        assert "1,234.56" in line

    def test_account_totals(self) -> None:
        at = ReportAccountTotals(rept_account_total=-500.00)
        line = at.format_line()
        assert "Account Total" in line
        assert "-500.00" in line

    def test_grand_totals(self) -> None:
        gt = ReportGrandTotals(rept_grand_total=9999.99)
        line = gt.format_line()
        assert "Grand Total" in line
        assert "9,999.99" in line
