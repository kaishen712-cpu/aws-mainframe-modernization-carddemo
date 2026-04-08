"""
Unit tests for cotrn02c.py — the Python translation of COTRN02C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by validation category.
"""

import unittest

from cotrn02c import (
    CardXrefRecord,
    InMemoryTransactionRepository,
    TransactionInput,
    TransactionRecord,
    add_transaction,
    build_transaction_record,
    clear_all_fields,
    copy_last_transaction_data,
    generate_transaction_id,
    get_header_info,
    validate_confirmation,
    validate_data_fields,
    validate_key_fields,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo_with_xref() -> InMemoryTransactionRepository:
    """Return a repo pre-loaded with one cross-reference record."""
    repo = InMemoryTransactionRepository()
    repo.add_xref(
        CardXrefRecord(
            card_num="4000123456789010",
            cust_id="000000001",
            acct_id="00000000001",
        )
    )
    return repo


def _valid_input(confirm: str = "Y") -> TransactionInput:
    """Return a fully valid TransactionInput ready to be added."""
    return TransactionInput(
        acct_id="",
        card_num="4000123456789010",
        tran_type_cd="01",
        tran_cat_cd="5000",
        tran_source="ONLINE",
        tran_desc="Test purchase at store",
        tran_amt="+00000100.50",
        orig_date="2024-06-15",
        proc_date="2024-06-16",
        merchant_id="123456789",
        merchant_name="ACME Store",
        merchant_city="Seattle",
        merchant_zip="98101",
        confirm=confirm,
    )


# ===========================================================================
# 1. Key-field validation
# ===========================================================================

class TestValidateKeyFields(unittest.TestCase):
    """Tests corresponding to VALIDATE-INPUT-KEY-FIELDS paragraph."""

    def test_account_id_resolves_card_number(self):
        """When account ID is provided, card number is looked up."""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="1", card_num="")
        result = validate_key_fields(inp, repo)

        self.assertTrue(result.is_valid)
        self.assertEqual(inp.card_num, "4000123456789010")

    def test_card_number_resolves_account_id(self):
        """When card number is provided, account ID is looked up."""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="", card_num="4000123456789010")
        result = validate_key_fields(inp, repo)

        self.assertTrue(result.is_valid)
        self.assertEqual(inp.acct_id, "00000000001")

    def test_neither_provided_returns_error(self):
        """Both blank → 'Account or Card Number must be entered...'"""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="", card_num="")
        result = validate_key_fields(inp, repo)

        self.assertFalse(result.is_valid)
        self.assertIn("Account or Card Number must be entered", result.error_message)

    def test_non_numeric_account_id(self):
        """Account ID with letters → 'Account ID must be Numeric...'"""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="ABC", card_num="")
        result = validate_key_fields(inp, repo)

        self.assertFalse(result.is_valid)
        self.assertIn("Account ID must be Numeric", result.error_message)

    def test_non_numeric_card_number(self):
        """Card Number with letters → 'Card Number must be Numeric...'"""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="", card_num="ABCD")
        result = validate_key_fields(inp, repo)

        self.assertFalse(result.is_valid)
        self.assertIn("Card Number must be Numeric", result.error_message)

    def test_account_id_not_found(self):
        """Valid numeric account but not in xref → 'Account ID NOT found...'"""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="99999999999", card_num="")
        result = validate_key_fields(inp, repo)

        self.assertFalse(result.is_valid)
        self.assertIn("Account ID NOT found", result.error_message)

    def test_card_number_not_found(self):
        """Valid numeric card but not in xref → 'Card Number NOT found...'"""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="", card_num="9999999999999999")
        result = validate_key_fields(inp, repo)

        self.assertFalse(result.is_valid)
        self.assertIn("Card Number NOT found", result.error_message)

    def test_account_id_takes_priority_over_card(self):
        """When both are provided, account ID path is used first."""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="1", card_num="9999999999999999")
        result = validate_key_fields(inp, repo)

        self.assertTrue(result.is_valid)
        # Card number overwritten by xref lookup
        self.assertEqual(inp.card_num, "4000123456789010")


# ===========================================================================
# 2. Data-field validation
# ===========================================================================

class TestValidateDataFields(unittest.TestCase):
    """Tests corresponding to VALIDATE-INPUT-DATA-FIELDS paragraph."""

    def _input_missing(self, field_name: str) -> TransactionInput:
        """Return a valid input with one field blanked out."""
        inp = _valid_input()
        setattr(inp, field_name, "")
        return inp

    # -- Required-field tests ------------------------------------------------

    def test_empty_type_cd(self):
        result = validate_data_fields(self._input_missing("tran_type_cd"))
        self.assertFalse(result.is_valid)
        self.assertIn("Type CD can NOT be empty", result.error_message)

    def test_empty_cat_cd(self):
        result = validate_data_fields(self._input_missing("tran_cat_cd"))
        self.assertFalse(result.is_valid)
        self.assertIn("Category CD can NOT be empty", result.error_message)

    def test_empty_source(self):
        result = validate_data_fields(self._input_missing("tran_source"))
        self.assertFalse(result.is_valid)
        self.assertIn("Source can NOT be empty", result.error_message)

    def test_empty_description(self):
        result = validate_data_fields(self._input_missing("tran_desc"))
        self.assertFalse(result.is_valid)
        self.assertIn("Description can NOT be empty", result.error_message)

    def test_empty_amount(self):
        result = validate_data_fields(self._input_missing("tran_amt"))
        self.assertFalse(result.is_valid)
        self.assertIn("Amount can NOT be empty", result.error_message)

    def test_empty_orig_date(self):
        result = validate_data_fields(self._input_missing("orig_date"))
        self.assertFalse(result.is_valid)
        self.assertIn("Orig Date can NOT be empty", result.error_message)

    def test_empty_proc_date(self):
        result = validate_data_fields(self._input_missing("proc_date"))
        self.assertFalse(result.is_valid)
        self.assertIn("Proc Date can NOT be empty", result.error_message)

    def test_empty_merchant_id(self):
        result = validate_data_fields(self._input_missing("merchant_id"))
        self.assertFalse(result.is_valid)
        self.assertIn("Merchant ID can NOT be empty", result.error_message)

    def test_empty_merchant_name(self):
        result = validate_data_fields(self._input_missing("merchant_name"))
        self.assertFalse(result.is_valid)
        self.assertIn("Merchant Name can NOT be empty", result.error_message)

    def test_empty_merchant_city(self):
        result = validate_data_fields(self._input_missing("merchant_city"))
        self.assertFalse(result.is_valid)
        self.assertIn("Merchant City can NOT be empty", result.error_message)

    def test_empty_merchant_zip(self):
        result = validate_data_fields(self._input_missing("merchant_zip"))
        self.assertFalse(result.is_valid)
        self.assertIn("Merchant Zip can NOT be empty", result.error_message)

    # -- Numeric-field tests -------------------------------------------------

    def test_non_numeric_type_cd(self):
        inp = _valid_input()
        inp.tran_type_cd = "AB"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Type CD must be Numeric", result.error_message)

    def test_non_numeric_cat_cd(self):
        inp = _valid_input()
        inp.tran_cat_cd = "ABCD"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Category CD must be Numeric", result.error_message)

    def test_non_numeric_merchant_id(self):
        inp = _valid_input()
        inp.merchant_id = "ABC"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Merchant ID must be Numeric", result.error_message)

    # -- Amount-format tests -------------------------------------------------

    def test_valid_positive_amount(self):
        inp = _valid_input()
        inp.tran_amt = "+00000100.50"
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_valid_negative_amount(self):
        inp = _valid_input()
        inp.tran_amt = "-00000025.00"
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_invalid_amount_no_sign(self):
        inp = _valid_input()
        inp.tran_amt = "000000100.50"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Amount should be in format", result.error_message)

    def test_invalid_amount_no_decimal(self):
        inp = _valid_input()
        inp.tran_amt = "+0000010050"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Amount should be in format", result.error_message)

    def test_invalid_amount_letters(self):
        inp = _valid_input()
        inp.tran_amt = "+0000ABCD.00"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Amount should be in format", result.error_message)

    # -- Date-format tests ---------------------------------------------------

    def test_valid_dates(self):
        inp = _valid_input()
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_invalid_orig_date_format(self):
        inp = _valid_input()
        inp.orig_date = "06/15/2024"  # wrong format
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Orig Date should be in format YYYY-MM-DD", result.error_message)

    def test_invalid_proc_date_format(self):
        inp = _valid_input()
        inp.proc_date = "2024/06/16"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Proc Date should be in format YYYY-MM-DD", result.error_message)

    def test_invalid_orig_date_calendar(self):
        """Format is correct but date doesn't exist (Feb 30)."""
        inp = _valid_input()
        inp.orig_date = "2024-02-30"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Orig Date - Not a valid date", result.error_message)

    def test_invalid_proc_date_calendar(self):
        """Format is correct but date doesn't exist (month 13)."""
        inp = _valid_input()
        inp.proc_date = "2024-13-01"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Proc Date - Not a valid date", result.error_message)

    # -- All-valid test ------------------------------------------------------

    def test_all_fields_valid(self):
        inp = _valid_input()
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_message, "")


# ===========================================================================
# 3. Confirmation validation
# ===========================================================================

class TestValidateConfirmation(unittest.TestCase):
    """Tests corresponding to the CONFIRM field logic in PROCESS-ENTER-KEY."""

    def test_confirm_Y(self):
        self.assertTrue(validate_confirmation("Y").is_valid)

    def test_confirm_y(self):
        self.assertTrue(validate_confirmation("y").is_valid)

    def test_confirm_N_prompts(self):
        result = validate_confirmation("N")
        self.assertFalse(result.is_valid)
        self.assertIn("Confirm to add this transaction", result.error_message)

    def test_confirm_n_prompts(self):
        result = validate_confirmation("n")
        self.assertFalse(result.is_valid)
        self.assertIn("Confirm to add this transaction", result.error_message)

    def test_confirm_blank_prompts(self):
        result = validate_confirmation("")
        self.assertFalse(result.is_valid)
        self.assertIn("Confirm to add this transaction", result.error_message)

    def test_confirm_spaces_prompts(self):
        result = validate_confirmation("   ")
        self.assertFalse(result.is_valid)
        self.assertIn("Confirm to add this transaction", result.error_message)

    def test_confirm_invalid_value(self):
        result = validate_confirmation("X")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid value. Valid values are (Y/N)", result.error_message)

    def test_confirm_invalid_digit(self):
        result = validate_confirmation("1")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid value", result.error_message)


# ===========================================================================
# 4. Transaction ID generation
# ===========================================================================

class TestGenerateTransactionId(unittest.TestCase):
    """Tests corresponding to the ID assignment in ADD-TRANSACTION."""

    def test_empty_file_starts_at_one(self):
        """If the TRANSACT file is empty, ID should be 0000000000000001."""
        repo = InMemoryTransactionRepository()
        tid = generate_transaction_id(repo)
        self.assertEqual(tid, "0000000000000001")

    def test_increments_from_last(self):
        """ID should be max existing + 1, zero-padded to 16 digits."""
        repo = InMemoryTransactionRepository()
        repo.add_transaction(TransactionRecord(tran_id="0000000000000042"))
        tid = generate_transaction_id(repo)
        self.assertEqual(tid, "0000000000000043")

    def test_handles_multiple_records(self):
        """Should find the true maximum even with non-sequential inserts."""
        repo = InMemoryTransactionRepository()
        repo.add_transaction(TransactionRecord(tran_id="0000000000000010"))
        repo.add_transaction(TransactionRecord(tran_id="0000000000000099"))
        repo.add_transaction(TransactionRecord(tran_id="0000000000000050"))
        tid = generate_transaction_id(repo)
        self.assertEqual(tid, "0000000000000100")


# ===========================================================================
# 5. Build transaction record
# ===========================================================================

class TestBuildTransactionRecord(unittest.TestCase):
    """Tests for building the TRAN-RECORD from validated screen input."""

    def test_fields_are_mapped_correctly(self):
        inp = _valid_input()
        inp.card_num = "4000123456789010"
        record = build_transaction_record("0000000000000001", inp)

        self.assertEqual(record.tran_id, "0000000000000001")
        self.assertEqual(record.tran_type_cd, "01")
        self.assertEqual(record.tran_cat_cd, "5000")
        self.assertEqual(record.tran_source, "ONLINE")
        self.assertEqual(record.tran_desc, "Test purchase at store")
        self.assertAlmostEqual(record.tran_amt, 100.50)
        self.assertEqual(record.tran_merchant_id, "123456789")
        self.assertEqual(record.tran_merchant_name, "ACME Store")
        self.assertEqual(record.tran_merchant_city, "Seattle")
        self.assertEqual(record.tran_merchant_zip, "98101")
        self.assertEqual(record.tran_card_num, "4000123456789010")
        self.assertEqual(record.tran_orig_ts, "2024-06-15")
        self.assertEqual(record.tran_proc_ts, "2024-06-16")

    def test_negative_amount_parsed(self):
        inp = _valid_input()
        inp.tran_amt = "-00000025.75"
        record = build_transaction_record("0000000000000001", inp)
        self.assertAlmostEqual(record.tran_amt, -25.75)


# ===========================================================================
# 6. Full add-transaction workflow
# ===========================================================================

class TestAddTransaction(unittest.TestCase):
    """End-to-end tests for the add_transaction function."""

    def test_successful_add(self):
        """Happy path: valid input with confirmation writes the record."""
        repo = _make_repo_with_xref()
        inp = _valid_input(confirm="Y")

        result = add_transaction(inp, repo)

        self.assertTrue(result.success)
        self.assertIn("Transaction added successfully", result.message)
        self.assertEqual(result.tran_id, "0000000000000001")
        # Verify record was persisted
        self.assertEqual(len(repo.transactions), 1)

    def test_sequential_adds_increment_id(self):
        """Adding two transactions yields IDs 1 and 2."""
        repo = _make_repo_with_xref()

        result1 = add_transaction(_valid_input(), repo)
        self.assertTrue(result1.success)
        self.assertEqual(result1.tran_id, "0000000000000001")

        result2 = add_transaction(_valid_input(), repo)
        self.assertTrue(result2.success)
        self.assertEqual(result2.tran_id, "0000000000000002")

    def test_rejected_without_confirmation(self):
        """No confirmation → transaction not written, prompt returned."""
        repo = _make_repo_with_xref()
        inp = _valid_input(confirm="")

        result = add_transaction(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("Confirm to add this transaction", result.message)
        self.assertEqual(len(repo.transactions), 0)

    def test_rejected_with_invalid_confirmation(self):
        """Bad confirmation value → error, no write."""
        repo = _make_repo_with_xref()
        inp = _valid_input(confirm="X")

        result = add_transaction(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("Invalid value", result.message)

    def test_rejected_invalid_key_field(self):
        """Non-numeric account → error before data validation."""
        repo = _make_repo_with_xref()
        inp = _valid_input()
        inp.card_num = ""
        inp.acct_id = "ABC"

        result = add_transaction(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("Account ID must be Numeric", result.message)

    def test_rejected_missing_data_field(self):
        """Empty description → error before confirmation check."""
        repo = _make_repo_with_xref()
        inp = _valid_input()
        inp.tran_desc = ""

        result = add_transaction(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("Description can NOT be empty", result.message)

    def test_rejected_bad_date(self):
        """Invalid calendar date → error."""
        repo = _make_repo_with_xref()
        inp = _valid_input()
        inp.orig_date = "2024-02-30"

        result = add_transaction(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("Orig Date - Not a valid date", result.message)

    def test_duplicate_key_error(self):
        """Force a duplicate by pre-loading the next ID."""
        repo = _make_repo_with_xref()
        repo.add_transaction(TransactionRecord(tran_id="0000000000000001"))

        # The generator will try to create ID 2, which doesn't exist yet,
        # so this should succeed.
        inp = _valid_input()
        result = add_transaction(inp, repo)
        self.assertTrue(result.success)
        self.assertEqual(result.tran_id, "0000000000000002")

    def test_success_message_contains_tran_id(self):
        """The success message should include the generated transaction ID."""
        repo = _make_repo_with_xref()
        repo.add_transaction(TransactionRecord(tran_id="0000000000000099"))

        result = add_transaction(_valid_input(), repo)

        self.assertTrue(result.success)
        self.assertIn("100", result.message)  # ID 100 displayed without leading zeros


# ===========================================================================
# 7. Copy last transaction data (PF5)
# ===========================================================================

class TestCopyLastTransactionData(unittest.TestCase):
    """Tests corresponding to the COPY-LAST-TRAN-DATA paragraph."""

    def test_copies_fields_from_last_transaction(self):
        """PF5 should populate data fields from the most recent record."""
        repo = _make_repo_with_xref()
        repo.add_transaction(TransactionRecord(
            tran_id="0000000000000001",
            tran_type_cd="02",
            tran_cat_cd="6000",
            tran_source="POS",
            tran_desc="Previous purchase",
            tran_amt=250.00,
            tran_merchant_id="987654321",
            tran_merchant_name="Old Store",
            tran_merchant_city="Portland",
            tran_merchant_zip="97201",
            tran_card_num="4000123456789010",
            tran_orig_ts="2024-05-01",
            tran_proc_ts="2024-05-02",
        ))

        inp = TransactionInput(card_num="4000123456789010")
        result = copy_last_transaction_data(inp, repo)

        self.assertIsNotNone(result)
        self.assertEqual(result.tran_type_cd, "02")
        self.assertEqual(result.tran_cat_cd, "6000")
        self.assertEqual(result.tran_source, "POS")
        self.assertEqual(result.tran_desc, "Previous purchase")
        self.assertEqual(result.merchant_id, "987654321")
        self.assertEqual(result.merchant_name, "Old Store")
        self.assertEqual(result.merchant_city, "Portland")
        self.assertEqual(result.merchant_zip, "97201")
        self.assertEqual(result.orig_date, "2024-05-01")
        self.assertEqual(result.proc_date, "2024-05-02")

    def test_returns_none_if_key_invalid(self):
        """PF5 with bad key fields returns None."""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="", card_num="")
        result = copy_last_transaction_data(inp, repo)
        self.assertIsNone(result)

    def test_returns_none_if_no_transactions(self):
        """PF5 with empty transaction file returns None."""
        repo = _make_repo_with_xref()
        inp = TransactionInput(card_num="4000123456789010")
        result = copy_last_transaction_data(inp, repo)
        self.assertIsNone(result)


# ===========================================================================
# 8. Clear screen / header helpers
# ===========================================================================

class TestClearAndHeaderHelpers(unittest.TestCase):
    """Tests for the PF4 clear and header-info functions."""

    def test_clear_all_fields_returns_blank_input(self):
        """PF4 should produce a completely blank TransactionInput."""
        blank = clear_all_fields()
        self.assertEqual(blank.acct_id, "")
        self.assertEqual(blank.card_num, "")
        self.assertEqual(blank.tran_type_cd, "")
        self.assertEqual(blank.tran_amt, "")
        self.assertEqual(blank.confirm, "")

    def test_header_info_contains_required_fields(self):
        """Header dict should have titles, program name, date, and time."""
        header = get_header_info()
        self.assertIn("title01", header)
        self.assertIn("title02", header)
        self.assertEqual(header["program_name"], "COTRN02C")
        self.assertEqual(header["transaction_id"], "CT02")
        # Date/time are dynamic but should be non-empty strings
        self.assertTrue(len(header["current_date"]) > 0)
        self.assertTrue(len(header["current_time"]) > 0)


# ===========================================================================
# 9. Edge cases and boundary conditions
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Additional boundary and edge-case tests."""

    def test_amount_zero(self):
        """Zero amount should be valid."""
        inp = _valid_input()
        inp.tran_amt = "+00000000.00"
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_amount_max_value(self):
        """Maximum representable amount: +99999999.99."""
        inp = _valid_input()
        inp.tran_amt = "+99999999.99"
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_amount_negative(self):
        """Negative amount (refund) should be valid."""
        inp = _valid_input()
        inp.tran_amt = "-00000050.00"
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_leap_year_date(self):
        """Feb 29 on a leap year is valid."""
        inp = _valid_input()
        inp.orig_date = "2024-02-29"
        result = validate_data_fields(inp)
        self.assertTrue(result.is_valid)

    def test_non_leap_year_feb29(self):
        """Feb 29 on a non-leap year is invalid."""
        inp = _valid_input()
        inp.orig_date = "2023-02-29"
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Orig Date - Not a valid date", result.error_message)

    def test_whitespace_only_field_treated_as_empty(self):
        """Fields with only spaces are treated as empty/missing."""
        inp = _valid_input()
        inp.tran_source = "   "
        result = validate_data_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Source can NOT be empty", result.error_message)

    def test_account_id_zero_padded(self):
        """A short account ID should be zero-padded to 11 digits."""
        repo = _make_repo_with_xref()
        inp = TransactionInput(acct_id="1")
        validate_key_fields(inp, repo)
        self.assertEqual(inp.acct_id, "00000000001")

    def test_card_number_zero_padded(self):
        """A short card number should be zero-padded to 16 digits."""
        repo = _make_repo_with_xref()
        repo.add_xref(CardXrefRecord(
            card_num="0000000000000001",
            cust_id="000000002",
            acct_id="00000000002",
        ))
        inp = TransactionInput(card_num="1")
        result = validate_key_fields(inp, repo)
        self.assertTrue(result.is_valid)
        self.assertEqual(inp.card_num, "0000000000000001")


if __name__ == "__main__":
    unittest.main()
