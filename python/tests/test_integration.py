"""
Integration tests exercising cross-program workflows.

These tests verify that multiple modules work together correctly,
simulating end-to-end scenarios that span several CardDemo programs.
"""

from __future__ import annotations

from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    TranCatBalRecord,
    TransactionRecord,
    UserSecurityRecord,
)
from python.models.commarea import CardDemoCommarea
from python.models.export_record import (
    ExportRecord,
    ExportCustomerData,
    ExportAccountData,
    ExportTransactionData,
    ExportCardXrefData,
    ExportCardData,
    EXPORT_REC_TYPE_CUSTOMER,
    EXPORT_REC_TYPE_ACCOUNT,
    EXPORT_REC_TYPE_TRANSACTION,
    EXPORT_REC_TYPE_CARD_XREF,
    EXPORT_REC_TYPE_CARD,
)
from python.models.report import (
    ReportNameHeader,
    TransactionDetailReport,
)
from python.common.menu import (
    get_main_menu_option,
    get_admin_menu_option,
    MAIN_MENU_OPTIONS,
)
from python.utils.date_validation import is_valid_calendar_date
from python.utils.string_utils import pad_left, safe_numeric, format_amount
from python.utils.lookup_codes import is_valid_us_state_code, is_valid_phone_area_code
from python.repositories.in_memory import (
    InMemoryAccountRepository,
    InMemoryCardRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
    InMemoryTransactionRepository,
)
from python.cotrn02c import (
    TransactionInput,
    add_transaction,
    validate_data_fields,
    copy_last_transaction_data,
    get_header_info,
    FoundationTransactionRepository,
)
from python.tests.conftest import (
    make_daily_transaction,
    make_user,
)


# ===================================================================
# 1. Sign-on -> Menu -> Transaction Add workflow
# ===================================================================

class TestSignOnMenuTransactionAdd:
    """Simulate: authenticate user -> select menu option -> add transaction."""

    def test_full_signon_menu_add_workflow(self, populated_system: dict) -> None:
        """End-to-end: sign on, navigate menu, add a transaction."""
        user_repo = populated_system["user_repo"]
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        # Step 1: Sign on — look up user credentials
        user = user_repo.lookup("USER0001")
        assert user is not None
        assert user.sec_usr_pwd == "usr12345"
        assert user.sec_usr_type == "U"

        # Step 2: Set up COMMAREA with user context
        commarea = CardDemoCommarea(
            cdemo_user_id="USER0001",
            cdemo_user_type="U",
            cdemo_pgm_context=0,
        )
        assert commarea.is_user
        assert commarea.is_program_enter

        # Step 3: Select menu option 8 (Transaction Add -> COTRN02C)
        menu_opt = get_main_menu_option(8)
        assert menu_opt is not None
        assert menu_opt.program_name == "COTRN02C"
        assert menu_opt.user_type == "U"

        # Step 4: Build COTRN02C-compatible repo from foundation repos
        foundation_repo = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        # Step 5: Add a transaction via COTRN02C business logic
        txn_input = TransactionInput(
            acct_id="00000000001",
            tran_type_cd="01",
            tran_cat_cd="5001",
            tran_source="ONLINE",
            tran_desc="Integration test purchase",
            tran_amt="+00000075.00",
            orig_date="2025-03-20",
            proc_date="2025-03-20",
            merchant_id="987654321",
            merchant_name="Integration Merchant",
            merchant_city="Boston",
            merchant_zip="02101",
            confirm="Y",
        )
        result = add_transaction(txn_input, foundation_repo)
        assert result.success is True
        assert result.tran_id != ""

        # Step 6: Verify transaction exists in the shared repo
        written = txn_repo.read_by_id(result.tran_id)
        assert written is not None
        assert written.tran_amt == 75.00
        assert written.tran_desc == "Integration test purchase"

    def test_menu_option_requires_user_type(self) -> None:
        """Verify menu options enforce user type."""
        # All main menu options require 'U' type
        for opt in MAIN_MENU_OPTIONS:
            assert opt.user_type == "U"

        # Admin user should not see main menu options (by convention)
        admin = CardDemoCommarea(cdemo_user_type="A")
        assert admin.is_admin
        assert not admin.is_user


# ===================================================================
# 2. Sign-on -> Account View -> Bill Payment workflow
# ===================================================================

class TestSignOnAccountBillPayment:
    """Simulate: authenticate -> view account -> make payment -> verify."""

    def test_account_view_and_payment(self, populated_system: dict) -> None:
        """Authenticate, view balance, make payment, verify update."""
        user_repo = populated_system["user_repo"]
        acct_repo = populated_system["account_repo"]

        # Step 1: Sign on
        user = user_repo.lookup("USER0001")
        assert user is not None

        # Step 2: Select Account View (option 1)
        menu_opt = get_main_menu_option(1)
        assert menu_opt is not None
        assert menu_opt.name == "Account View"

        # Step 3: View account balance
        account = acct_repo.lookup_by_id("00000000001")
        assert account is not None
        original_balance = account.acct_curr_bal
        assert original_balance == 1500.00

        # Step 4: Select Bill Payment (option 10)
        payment_opt = get_main_menu_option(10)
        assert payment_opt is not None
        assert payment_opt.name == "Bill Payment"

        # Step 5: Make a payment — reduce balance
        payment_amount = 200.00
        updated_account = AccountRecord(
            acct_id=account.acct_id,
            acct_active_status=account.acct_active_status,
            acct_curr_bal=account.acct_curr_bal - payment_amount,
            acct_credit_limit=account.acct_credit_limit,
            acct_cash_credit_limit=account.acct_cash_credit_limit,
            acct_open_date=account.acct_open_date,
            acct_expiration_date=account.acct_expiration_date,
            acct_reissue_date=account.acct_reissue_date,
            acct_curr_cyc_credit=account.acct_curr_cyc_credit + payment_amount,
            acct_curr_cyc_debit=account.acct_curr_cyc_debit,
            acct_addr_zip=account.acct_addr_zip,
            acct_group_id=account.acct_group_id,
        )
        assert acct_repo.update(updated_account) is True

        # Step 6: Verify updated balance
        refreshed = acct_repo.lookup_by_id("00000000001")
        assert refreshed is not None
        assert refreshed.acct_curr_bal == 1300.00
        assert refreshed.acct_curr_cyc_credit == payment_amount


# ===================================================================
# 3. User CRUD cycle
# ===================================================================

class TestUserCrudCycle:
    """Simulate: add user -> list -> update -> verify -> delete -> verify."""

    def test_full_user_crud(self, populated_system: dict) -> None:
        """Complete CRUD lifecycle for a user security record."""
        user_repo = populated_system["user_repo"]

        # Step 1: Verify admin can access User Add (admin menu option 2)
        admin_opt = get_admin_menu_option(2)
        assert admin_opt is not None
        assert admin_opt.name == "User Add (Security)"

        # Step 2: Add a new user
        new_user = make_user(
            user_id="NEWUSR01",
            first="New",
            last="Person",
            password="newp1234",
            user_type="U",
        )
        assert user_repo.add(new_user) is True

        # Step 3: List users and verify new user appears
        all_users = user_repo.list_all()
        user_ids = [u.sec_usr_id for u in all_users]
        assert "NEWUSR01" in user_ids
        assert "ADMIN001" in user_ids
        assert "USER0001" in user_ids

        # Step 4: Update the user (admin menu option 3)
        update_opt = get_admin_menu_option(3)
        assert update_opt is not None
        assert update_opt.name == "User Update (Security)"

        updated_user = UserSecurityRecord(
            sec_usr_id="NEWUSR01",
            sec_usr_fname="Updated",
            sec_usr_lname="Person",
            sec_usr_pwd="updt1234",
            sec_usr_type="A",
        )
        assert user_repo.update(updated_user) is True

        # Step 5: Verify update
        refreshed = user_repo.lookup("NEWUSR01")
        assert refreshed is not None
        assert refreshed.sec_usr_fname == "Updated"
        assert refreshed.sec_usr_type == "A"

        # Step 6: Delete the user (admin menu option 4)
        delete_opt = get_admin_menu_option(4)
        assert delete_opt is not None
        assert delete_opt.name == "User Delete (Security)"
        assert user_repo.delete("NEWUSR01") is True

        # Step 7: Verify deleted
        assert user_repo.lookup("NEWUSR01") is None
        remaining = user_repo.list_all()
        remaining_ids = [u.sec_usr_id for u in remaining]
        assert "NEWUSR01" not in remaining_ids


# ===================================================================
# 4. Card lookup chain
# ===================================================================

class TestCardLookupChain:
    """Simulate: card -> account via xref -> customer -> verify consistency."""

    def test_card_to_account_to_customer(self, populated_system: dict) -> None:
        """Follow the lookup chain: card -> xref -> account -> customer."""
        card_repo = populated_system["card_repo"]
        xref_repo = populated_system["card_xref_repo"]
        acct_repo = populated_system["account_repo"]
        cust_repo = populated_system["customer_repo"]

        # Step 1: Look up card
        card = card_repo.lookup_by_card_num("4111111111111111")
        assert card is not None
        assert card.card_active_status == "Y"
        assert card.card_embossed_name == "JOHN DOE"

        # Step 2: Get account via cross-reference
        xref = xref_repo.lookup_by_card_num("4111111111111111")
        assert xref is not None
        assert xref.xref_acct_id == "00000000001"
        assert xref.xref_cust_id == "000000001"

        # Step 3: Verify account ID from xref matches card's account
        assert card.card_acct_id == xref.xref_acct_id

        # Step 4: Look up the account
        account = acct_repo.lookup_by_id(xref.xref_acct_id)
        assert account is not None
        assert account.acct_active_status == "Y"

        # Step 5: Look up the customer
        customer = cust_repo.lookup_by_id(xref.xref_cust_id)
        assert customer is not None
        assert customer.cust_first_name == "John"
        assert customer.cust_last_name == "Doe"

        # Step 6: Verify address data is consistent with state validation
        assert is_valid_us_state_code(customer.cust_addr_state_cd)

    def test_reverse_lookup_account_to_card(self, populated_system: dict) -> None:
        """Reverse lookup: account -> xref -> card."""
        xref_repo = populated_system["card_xref_repo"]
        card_repo = populated_system["card_repo"]

        xref = xref_repo.lookup_by_acct_id("00000000002")
        assert xref is not None
        assert xref.xref_card_num == "4222222222222222"

        card = card_repo.lookup_by_card_num(xref.xref_card_num)
        assert card is not None
        assert card.card_embossed_name == "JANE SMITH"


# ===================================================================
# 5. Transaction lifecycle
# ===================================================================

class TestTransactionLifecycle:
    """Simulate: add transaction -> list -> view details -> verify."""

    def test_add_list_view_transaction(self, populated_system: dict) -> None:
        """Add a transaction, list by card, view details, verify fields."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        # Step 1: Use FoundationTransactionRepository adapter
        foundation_repo = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        # Step 2: Add a new transaction
        txn_input = TransactionInput(
            acct_id="00000000001",
            tran_type_cd="01",
            tran_cat_cd="5001",
            tran_source="POS",
            tran_desc="Coffee shop purchase",
            tran_amt="+00000004.50",
            orig_date="2025-04-01",
            proc_date="2025-04-01",
            merchant_id="555555555",
            merchant_name="Coffee Corner",
            merchant_city="Manhattan",
            merchant_zip="10002",
            confirm="Y",
        )
        result = add_transaction(txn_input, foundation_repo)
        assert result.success is True

        # Step 3: List transactions for the card (menu option 6)
        list_opt = get_main_menu_option(6)
        assert list_opt is not None
        assert list_opt.name == "Transaction List"

        card_txns = txn_repo.list_by_card("4111111111111111")
        # Should have original 2 + new 1
        assert len(card_txns) >= 3

        # Step 4: View transaction details (menu option 7)
        view_opt = get_main_menu_option(7)
        assert view_opt is not None
        assert view_opt.name == "Transaction View"

        detail = txn_repo.read_by_id(result.tran_id)
        assert detail is not None
        assert detail.tran_desc == "Coffee shop purchase"
        assert detail.tran_amt == 4.50
        assert detail.tran_merchant_name == "Coffee Corner"
        assert detail.tran_card_num == "4111111111111111"

    def test_copy_last_transaction_via_foundation(self, populated_system: dict) -> None:
        """Test the PF5 copy-last-transaction feature via the adapter."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        foundation_repo = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        txn_input = TransactionInput(acct_id="00000000001")
        result = copy_last_transaction_data(txn_input, foundation_repo)
        assert result is not None
        # Should have copied data from the last transaction
        assert result.tran_type_cd != ""
        assert result.tran_desc != ""


# ===================================================================
# 6. Batch posting
# ===================================================================

class TestBatchPosting:
    """Simulate: create daily transactions -> post to main file -> verify."""

    def test_daily_transaction_posting(self, populated_system: dict) -> None:
        """Simulate batch posting: daily transactions -> main transaction file."""
        daily_repo = populated_system["daily_transaction_repo"]
        txn_repo = populated_system["transaction_repo"]
        acct_repo = populated_system["account_repo"]
        tcbal_repo = populated_system["tran_cat_bal_repo"]

        # Step 1: Create daily transactions
        daily1 = make_daily_transaction(
            tran_id="0000000000000101",
            card_num="4111111111111111",
            amount=45.00,
        )
        daily2 = make_daily_transaction(
            tran_id="0000000000000102",
            card_num="4111111111111111",
            amount=60.00,
        )
        daily_repo.seed(daily1)
        daily_repo.seed(daily2)

        # Step 2: Read all daily transactions (simulates batch read)
        daily_txns = daily_repo.read_all()
        assert len(daily_txns) >= 2

        # Step 3: Post each daily transaction to the main transaction file
        posted_count = 0
        total_posted_amount = 0.0
        for dtxn in daily_txns:
            main_txn = TransactionRecord(
                tran_id=dtxn.dalytran_id,
                tran_type_cd=dtxn.dalytran_type_cd,
                tran_cat_cd=dtxn.dalytran_cat_cd,
                tran_source=dtxn.dalytran_source,
                tran_desc=dtxn.dalytran_desc,
                tran_amt=dtxn.dalytran_amt,
                tran_merchant_id=dtxn.dalytran_merchant_id,
                tran_merchant_name=dtxn.dalytran_merchant_name,
                tran_merchant_city=dtxn.dalytran_merchant_city,
                tran_merchant_zip=dtxn.dalytran_merchant_zip,
                tran_card_num=dtxn.dalytran_card_num,
                tran_orig_ts=dtxn.dalytran_orig_ts,
                tran_proc_ts=dtxn.dalytran_proc_ts,
            )
            if txn_repo.write(main_txn):
                posted_count += 1
                total_posted_amount += dtxn.dalytran_amt

        assert posted_count >= 2

        # Step 4: Verify main transaction file updated
        posted1 = txn_repo.read_by_id("0000000000000101")
        assert posted1 is not None
        assert posted1.tran_amt == 45.00

        posted2 = txn_repo.read_by_id("0000000000000102")
        assert posted2 is not None
        assert posted2.tran_amt == 60.00

        # Step 5: Update account balance (simulates CBTRN03C posting)
        account = acct_repo.lookup_by_id("00000000001")
        assert account is not None
        original_bal = account.acct_curr_bal

        updated_account = AccountRecord(
            acct_id=account.acct_id,
            acct_active_status=account.acct_active_status,
            acct_curr_bal=account.acct_curr_bal + total_posted_amount,
            acct_credit_limit=account.acct_credit_limit,
            acct_cash_credit_limit=account.acct_cash_credit_limit,
            acct_open_date=account.acct_open_date,
            acct_expiration_date=account.acct_expiration_date,
            acct_reissue_date=account.acct_reissue_date,
            acct_curr_cyc_credit=account.acct_curr_cyc_credit,
            acct_curr_cyc_debit=account.acct_curr_cyc_debit + total_posted_amount,
            acct_addr_zip=account.acct_addr_zip,
            acct_group_id=account.acct_group_id,
        )
        assert acct_repo.update(updated_account) is True

        # Step 6: Verify account balance updated
        refreshed = acct_repo.lookup_by_id("00000000001")
        assert refreshed is not None
        assert refreshed.acct_curr_bal == original_bal + total_posted_amount

        # Step 7: Update category balance
        cat_bal = tcbal_repo.lookup("00000000001", "SA", "5001")
        assert cat_bal is not None
        original_cat_bal = cat_bal.tran_cat_bal
        updated_cat_bal = TranCatBalRecord(
            trancat_acct_id="00000000001",
            trancat_type_cd="SA",
            trancat_cd="5001",
            tran_cat_bal=original_cat_bal + total_posted_amount,
        )
        assert tcbal_repo.update(updated_cat_bal) is True
        refreshed_cat = tcbal_repo.lookup("00000000001", "SA", "5001")
        assert refreshed_cat is not None
        assert refreshed_cat.tran_cat_bal == original_cat_bal + total_posted_amount


# ===================================================================
# 7. Export -> Import round trip
# ===================================================================

class TestExportImportRoundTrip:
    """Simulate: export all data -> import to fresh repos -> verify."""

    def test_export_import_customers(self, populated_system: dict) -> None:
        """Export customer data and reimport to fresh repository."""
        cust_repo = populated_system["customer_repo"]

        # Step 1: Export — read all known customer records
        cust1 = cust_repo.lookup_by_id("000000001")
        cust2 = cust_repo.lookup_by_id("000000002")
        assert cust1 is not None
        assert cust2 is not None

        # Step 2: Build export records
        exports = []
        for cust in [cust1, cust2]:
            export = ExportRecord(
                export_rec_type=EXPORT_REC_TYPE_CUSTOMER,
                export_timestamp="2025-04-01 12:00:00.000000",
                export_sequence_num=len(exports) + 1,
                export_branch_id="BR01",
                export_region_code="EAST",
                record_data=ExportCustomerData(
                    exp_cust_id=int(cust.cust_id),
                    exp_cust_first_name=cust.cust_first_name,
                    exp_cust_last_name=cust.cust_last_name,
                    exp_cust_addr_state_cd=cust.cust_addr_state_cd,
                    exp_cust_ssn=cust.cust_ssn,
                    exp_cust_dob_yyyy_mm_dd=cust.cust_dob_yyyy_mm_dd,
                ),
            )
            exports.append(export)

        assert len(exports) == 2

        # Step 3: Import to fresh repository
        new_cust_repo = InMemoryCustomerRepository()
        for exp in exports:
            data = exp.record_data
            assert isinstance(data, ExportCustomerData)
            imported = CustomerRecord(
                cust_id=str(data.exp_cust_id).zfill(9),
                cust_first_name=data.exp_cust_first_name,
                cust_last_name=data.exp_cust_last_name,
                cust_addr_state_cd=data.exp_cust_addr_state_cd,
                cust_ssn=data.exp_cust_ssn,
                cust_dob_yyyy_mm_dd=data.exp_cust_dob_yyyy_mm_dd,
            )
            new_cust_repo.seed(imported)

        # Step 4: Verify all records match originals
        reimported1 = new_cust_repo.lookup_by_id("000000001")
        assert reimported1 is not None
        assert reimported1.cust_first_name == cust1.cust_first_name
        assert reimported1.cust_last_name == cust1.cust_last_name

        reimported2 = new_cust_repo.lookup_by_id("000000002")
        assert reimported2 is not None
        assert reimported2.cust_first_name == cust2.cust_first_name

    def test_export_import_accounts(self, populated_system: dict) -> None:
        """Export account data and reimport to fresh repository."""
        acct_repo = populated_system["account_repo"]

        acct1 = acct_repo.lookup_by_id("00000000001")
        acct2 = acct_repo.lookup_by_id("00000000002")
        assert acct1 is not None
        assert acct2 is not None

        # Export
        exports = []
        for acct in [acct1, acct2]:
            export = ExportRecord(
                export_rec_type=EXPORT_REC_TYPE_ACCOUNT,
                export_timestamp="2025-04-01 12:00:00.000000",
                export_sequence_num=len(exports) + 1,
                record_data=ExportAccountData(
                    exp_acct_id=acct.acct_id,
                    exp_acct_active_status=acct.acct_active_status,
                    exp_acct_curr_bal=acct.acct_curr_bal,
                    exp_acct_credit_limit=acct.acct_credit_limit,
                ),
            )
            exports.append(export)

        # Import to fresh repo
        new_repo = InMemoryAccountRepository()
        for exp in exports:
            data = exp.record_data
            assert isinstance(data, ExportAccountData)
            new_repo.seed(AccountRecord(
                acct_id=data.exp_acct_id,
                acct_active_status=data.exp_acct_active_status,
                acct_curr_bal=data.exp_acct_curr_bal,
                acct_credit_limit=data.exp_acct_credit_limit,
            ))

        # Verify
        r1 = new_repo.lookup_by_id("00000000001")
        assert r1 is not None
        assert r1.acct_curr_bal == acct1.acct_curr_bal

        r2 = new_repo.lookup_by_id("00000000002")
        assert r2 is not None
        assert r2.acct_curr_bal == acct2.acct_curr_bal

    def test_export_import_transactions(self, populated_system: dict) -> None:
        """Export transactions and reimport to fresh repository."""
        txn_repo = populated_system["transaction_repo"]

        # Read all known transactions
        txn1 = txn_repo.read_by_id("0000000000000001")
        txn2 = txn_repo.read_by_id("0000000000000002")
        txn3 = txn_repo.read_by_id("0000000000000003")
        assert txn1 is not None
        assert txn2 is not None
        assert txn3 is not None

        # Export
        exports = []
        for txn in [txn1, txn2, txn3]:
            export = ExportRecord(
                export_rec_type=EXPORT_REC_TYPE_TRANSACTION,
                export_timestamp="2025-04-01 12:00:00.000000",
                export_sequence_num=len(exports) + 1,
                record_data=ExportTransactionData(
                    exp_tran_id=txn.tran_id,
                    exp_tran_type_cd=txn.tran_type_cd,
                    exp_tran_cat_cd=txn.tran_cat_cd,
                    exp_tran_amt=txn.tran_amt,
                    exp_tran_card_num=txn.tran_card_num,
                    exp_tran_desc=txn.tran_desc,
                ),
            )
            exports.append(export)

        # Import
        new_repo = InMemoryTransactionRepository()
        for exp in exports:
            data = exp.record_data
            assert isinstance(data, ExportTransactionData)
            new_repo.seed(TransactionRecord(
                tran_id=data.exp_tran_id,
                tran_type_cd=data.exp_tran_type_cd,
                tran_cat_cd=data.exp_tran_cat_cd,
                tran_amt=data.exp_tran_amt,
                tran_card_num=data.exp_tran_card_num,
                tran_desc=data.exp_tran_desc,
            ))

        # Verify
        for orig_id in ["0000000000000001", "0000000000000002", "0000000000000003"]:
            original = txn_repo.read_by_id(orig_id)
            reimported = new_repo.read_by_id(orig_id)
            assert reimported is not None
            assert original is not None
            assert reimported.tran_amt == original.tran_amt
            assert reimported.tran_type_cd == original.tran_type_cd

    def test_export_import_card_xrefs(self, populated_system: dict) -> None:
        """Export card cross-references and reimport."""
        xref_repo = populated_system["card_xref_repo"]

        xref1 = xref_repo.lookup_by_card_num("4111111111111111")
        xref2 = xref_repo.lookup_by_card_num("4222222222222222")
        assert xref1 is not None
        assert xref2 is not None

        # Export
        exports = []
        for xref in [xref1, xref2]:
            export = ExportRecord(
                export_rec_type=EXPORT_REC_TYPE_CARD_XREF,
                export_timestamp="2025-04-01 12:00:00.000000",
                export_sequence_num=len(exports) + 1,
                record_data=ExportCardXrefData(
                    exp_xref_card_num=xref.xref_card_num,
                    exp_xref_cust_id=xref.xref_cust_id,
                    exp_xref_acct_id=int(xref.xref_acct_id),
                ),
            )
            exports.append(export)

        # Import
        new_repo = InMemoryCardXrefRepository()
        for exp in exports:
            data = exp.record_data
            assert isinstance(data, ExportCardXrefData)
            new_repo.seed(CardXrefRecord(
                xref_card_num=data.exp_xref_card_num,
                xref_cust_id=data.exp_xref_cust_id,
                xref_acct_id=str(data.exp_xref_acct_id).zfill(11),
            ))

        # Verify
        r1 = new_repo.lookup_by_card_num("4111111111111111")
        assert r1 is not None
        assert r1.xref_acct_id == xref1.xref_acct_id

    def test_export_import_cards(self, populated_system: dict) -> None:
        """Export cards and reimport."""
        card_repo = populated_system["card_repo"]

        card1 = card_repo.lookup_by_card_num("4111111111111111")
        card2 = card_repo.lookup_by_card_num("4222222222222222")
        assert card1 is not None
        assert card2 is not None

        # Export
        exports = []
        for card in [card1, card2]:
            export = ExportRecord(
                export_rec_type=EXPORT_REC_TYPE_CARD,
                export_timestamp="2025-04-01 12:00:00.000000",
                export_sequence_num=len(exports) + 1,
                record_data=ExportCardData(
                    exp_card_num=card.card_num,
                    exp_card_acct_id=int(card.card_acct_id),
                    exp_card_cvv_cd=int(card.card_cvv_cd),
                    exp_card_embossed_name=card.card_embossed_name,
                    exp_card_active_status=card.card_active_status,
                ),
            )
            exports.append(export)

        # Import
        new_repo = InMemoryCardRepository()
        for exp in exports:
            data = exp.record_data
            assert isinstance(data, ExportCardData)
            new_repo.seed(CardRecord(
                card_num=data.exp_card_num,
                card_acct_id=str(data.exp_card_acct_id).zfill(11),
                card_cvv_cd=str(data.exp_card_cvv_cd).zfill(3),
                card_embossed_name=data.exp_card_embossed_name,
                card_active_status=data.exp_card_active_status,
            ))

        # Verify
        r1 = new_repo.lookup_by_card_num("4111111111111111")
        assert r1 is not None
        assert r1.card_embossed_name == card1.card_embossed_name

        r2 = new_repo.lookup_by_card_num("4222222222222222")
        assert r2 is not None
        assert r2.card_embossed_name == card2.card_embossed_name


# ===================================================================
# 8. Cross-module utility integration
# ===================================================================

class TestCrossModuleUtilities:
    """Verify utilities work correctly across modules."""

    def test_date_validation_in_transaction_flow(self) -> None:
        """Date validation integrates with transaction add flow."""
        # Valid date passes
        assert is_valid_calendar_date("20250315") is True

        # Invalid date fails
        assert is_valid_calendar_date("20250230") is False

        # This should also be caught by COTRN02C's validate_data_fields
        txn_input = TransactionInput(
            acct_id="00000000001",
            card_num="4111111111111111",
            tran_type_cd="01",
            tran_cat_cd="5001",
            tran_source="ONLINE",
            tran_desc="Test",
            tran_amt="+00000010.00",
            orig_date="2025-02-30",
            proc_date="2025-03-15",
            merchant_id="123456789",
            merchant_name="Test",
            merchant_city="NYC",
            merchant_zip="10001",
        )
        result = validate_data_fields(txn_input)
        assert result.is_valid is False
        assert "Orig Date" in result.error_message

    def test_string_utils_with_record_fields(self) -> None:
        """String utilities work with record field formatting."""
        # Pad account ID to 11 digits
        assert pad_left("1", 11) == "00000000001"

        # Pad card number to 16 digits
        assert pad_left("4111111111111111", 16) == "4111111111111111"

        # Format amount
        assert format_amount(100.50) == "+00000100.50"
        assert format_amount(-25.00) == "-00000025.00"

        # Safe numeric parsing
        assert safe_numeric("00000000001") == 1
        assert safe_numeric("invalid", default=0) == 0

    def test_lookup_codes_with_customer_data(self, populated_system: dict) -> None:
        """Lookup code validation works with customer records."""
        cust_repo = populated_system["customer_repo"]

        cust = cust_repo.lookup_by_id("000000001")
        assert cust is not None

        # Validate state code
        assert is_valid_us_state_code(cust.cust_addr_state_cd)
        assert is_valid_us_state_code("NY")
        assert not is_valid_us_state_code("XX")

        # Validate phone area code
        assert is_valid_phone_area_code("212")
        assert not is_valid_phone_area_code("000")

    def test_report_formatting_with_transaction_data(self, populated_system: dict) -> None:
        """Report formatting uses transaction data correctly."""
        txn_repo = populated_system["transaction_repo"]
        ttype_repo = populated_system["tran_type_repo"]
        tcat_repo = populated_system["tran_cat_repo"]

        # Read a transaction
        txn = txn_repo.read_by_id("0000000000000001")
        assert txn is not None

        # Look up type and category descriptions
        ttype = ttype_repo.lookup(txn.tran_type_cd)
        assert ttype is not None

        tcat = tcat_repo.lookup(txn.tran_type_cd, txn.tran_cat_cd)
        assert tcat is not None

        # Build a report detail line
        detail = TransactionDetailReport(
            tran_report_trans_id=txn.tran_id,
            tran_report_account_id="00000000001",
            tran_report_type_cd=txn.tran_type_cd,
            tran_report_type_desc=ttype.tran_type_desc,
            tran_report_cat_cd=txn.tran_cat_cd,
            tran_report_cat_desc=tcat.tran_cat_type_desc,
            tran_report_source=txn.tran_source,
            tran_report_amt=txn.tran_amt,
        )
        line = detail.format_line()
        assert txn.tran_id in line
        assert ttype.tran_type_desc in line

        # Build report header
        header = ReportNameHeader(
            rept_start_date="2025-03-01",
            rept_end_date="2025-03-31",
        )
        header_line = header.format_header()
        assert "Daily Transaction Report" in header_line
        assert "2025-03-01" in header_line

    def test_commarea_workflow(self) -> None:
        """COMMAREA correctly tracks program navigation context."""
        # Simulate sign-on program setting context
        commarea = CardDemoCommarea(
            cdemo_user_id="USER0001",
            cdemo_user_type="U",
            cdemo_pgm_context=0,
            cdemo_from_program="COSGN00C",
            cdemo_to_program="COMEN01C",
        )
        assert commarea.is_program_enter
        assert commarea.is_user

        # Navigate to transaction add
        commarea.cdemo_from_program = "COMEN01C"
        commarea.cdemo_to_program = "COTRN02C"
        commarea.cdemo_pgm_context = 1
        assert commarea.is_program_reenter
        assert commarea.cdemo_to_program == "COTRN02C"

        # Set card/account context
        commarea.cdemo_acct_id = "00000000001"
        commarea.cdemo_card_num = "4111111111111111"
        assert commarea.cdemo_acct_id == "00000000001"

    def test_header_info_integration(self) -> None:
        """get_header_info produces consistent header data."""
        header = get_header_info()
        assert "AWS Mainframe Modernization" in header["title01"]
        assert "CardDemo" in header["title02"]
        assert header["program_name"] == "COTRN02C"
        assert header["transaction_id"] == "CT02"
        # Date and time should be populated
        assert len(header["current_date"]) == 8  # MM/DD/YY
        assert len(header["current_time"]) == 8  # HH:MM:SS


# ===================================================================
# 9. FoundationTransactionRepository adapter tests
# ===================================================================

class TestFoundationTransactionRepositoryAdapter:
    """Test the adapter that bridges shared repos to COTRN02C interface."""

    def test_adapter_lookup_card_by_account(self, populated_system: dict) -> None:
        """Adapter correctly looks up card by account."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        adapter = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        result = adapter.lookup_card_by_account("00000000001")
        assert result is not None
        assert result.card_num == "4111111111111111"
        assert result.acct_id == "00000000001"

    def test_adapter_lookup_account_by_card(self, populated_system: dict) -> None:
        """Adapter correctly looks up account by card."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        adapter = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        result = adapter.lookup_account_by_card("4222222222222222")
        assert result is not None
        assert result.acct_id == "00000000002"

    def test_adapter_not_found_returns_none(self, populated_system: dict) -> None:
        """Adapter returns None for missing records."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        adapter = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        assert adapter.lookup_card_by_account("99999999999") is None
        assert adapter.lookup_account_by_card("9999999999999999") is None

    def test_adapter_write_and_read_transaction(self, populated_system: dict) -> None:
        """Adapter can write transactions that the shared repo can read."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        adapter = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        # Write through adapter
        txn = TransactionRecord(
            tran_id="0000000000099999",
            tran_amt=999.99,
            tran_desc="Adapter test",
        )
        assert adapter.write_transaction(txn) is True

        # Read through shared repo
        result = txn_repo.read_by_id("0000000000099999")
        assert result is not None
        assert result.tran_amt == 999.99

    def test_adapter_get_max_id(self, populated_system: dict) -> None:
        """Adapter delegates get_max_transaction_id correctly."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        adapter = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        max_id = adapter.get_max_transaction_id()
        assert max_id == txn_repo.get_max_id()
        assert max_id >= 3  # At least 3 transactions in the populated system

    def test_adapter_get_last_transaction(self, populated_system: dict) -> None:
        """Adapter delegates get_last_transaction correctly."""
        xref_repo = populated_system["card_xref_repo"]
        txn_repo = populated_system["transaction_repo"]

        adapter = FoundationTransactionRepository(
            xref_repo=xref_repo,
            txn_repo=txn_repo,
        )

        last = adapter.get_last_transaction()
        assert last is not None
        expected = txn_repo.get_last_transaction()
        assert expected is not None
        assert last.tran_id == expected.tran_id
