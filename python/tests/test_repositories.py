"""
Unit tests for all in-memory repository implementations.

Covers CRUD operations, edge cases, not-found scenarios, and seed helpers.
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
    TransactionRecord,
    TransactionTypeRecord,
    UserSecurityRecord,
)
from python.repositories.in_memory import (
    InMemoryAccountRepository,
    InMemoryCardRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
    InMemoryDailyTransactionRepository,
    InMemoryDisclosureGroupRepository,
    InMemoryTranCatBalRepository,
    InMemoryTransactionCategoryRepository,
    InMemoryTransactionRepository,
    InMemoryTransactionTypeRepository,
    InMemoryUserSecurityRepository,
)


# ===================================================================
# AccountRepository
# ===================================================================

class TestInMemoryAccountRepository:
    """Tests for InMemoryAccountRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryAccountRepository()
        assert repo.lookup_by_id("99999999999") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryAccountRepository()
        rec = AccountRecord(acct_id="00000000001", acct_active_status="Y")
        repo.seed(rec)
        result = repo.lookup_by_id("00000000001")
        assert result is not None
        assert result.acct_active_status == "Y"

    def test_update_existing(self) -> None:
        repo = InMemoryAccountRepository()
        rec = AccountRecord(acct_id="00000000001", acct_curr_bal=100.0)
        repo.seed(rec)
        updated = AccountRecord(acct_id="00000000001", acct_curr_bal=200.0)
        assert repo.update(updated) is True
        result = repo.lookup_by_id("00000000001")
        assert result is not None
        assert result.acct_curr_bal == 200.0

    def test_update_not_found(self) -> None:
        repo = InMemoryAccountRepository()
        rec = AccountRecord(acct_id="00000000099")
        assert repo.update(rec) is False

    def test_list_all_empty(self) -> None:
        repo = InMemoryAccountRepository()
        assert repo.list_all() == []

    def test_list_all(self) -> None:
        repo = InMemoryAccountRepository()
        repo.seed(AccountRecord(acct_id="00000000001"))
        repo.seed(AccountRecord(acct_id="00000000002"))
        assert len(repo.list_all()) == 2


# ===================================================================
# CardRepository
# ===================================================================

class TestInMemoryCardRepository:
    """Tests for InMemoryCardRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryCardRepository()
        assert repo.lookup_by_card_num("0000000000000000") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryCardRepository()
        card = CardRecord(card_num="4111111111111111", card_acct_id="00000000001")
        repo.seed(card)
        result = repo.lookup_by_card_num("4111111111111111")
        assert result is not None
        assert result.card_acct_id == "00000000001"

    def test_list_by_account(self) -> None:
        repo = InMemoryCardRepository()
        repo.seed(CardRecord(card_num="4111111111111111", card_acct_id="00000000001"))
        repo.seed(CardRecord(card_num="4222222222222222", card_acct_id="00000000001"))
        repo.seed(CardRecord(card_num="4333333333333333", card_acct_id="00000000002"))
        cards = repo.list_by_account("00000000001")
        assert len(cards) == 2

    def test_list_by_account_empty(self) -> None:
        repo = InMemoryCardRepository()
        assert repo.list_by_account("00000000099") == []


# ===================================================================
# CardXrefRepository
# ===================================================================

class TestInMemoryCardXrefRepository:
    """Tests for InMemoryCardXrefRepository."""

    def test_lookup_by_card_not_found(self) -> None:
        repo = InMemoryCardXrefRepository()
        assert repo.lookup_by_card_num("0000000000000000") is None

    def test_lookup_by_acct_not_found(self) -> None:
        repo = InMemoryCardXrefRepository()
        assert repo.lookup_by_acct_id("00000000099") is None

    def test_seed_and_lookup_by_card(self) -> None:
        repo = InMemoryCardXrefRepository()
        xref = CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )
        repo.seed(xref)
        result = repo.lookup_by_card_num("4111111111111111")
        assert result is not None
        assert result.xref_cust_id == "000000001"

    def test_seed_and_lookup_by_acct(self) -> None:
        repo = InMemoryCardXrefRepository()
        xref = CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )
        repo.seed(xref)
        result = repo.lookup_by_acct_id("00000000001")
        assert result is not None
        assert result.xref_card_num == "4111111111111111"


# ===================================================================
# CustomerRepository
# ===================================================================

class TestInMemoryCustomerRepository:
    """Tests for InMemoryCustomerRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryCustomerRepository()
        assert repo.lookup_by_id("000000099") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryCustomerRepository()
        cust = CustomerRecord(cust_id="000000001", cust_first_name="Jane")
        repo.seed(cust)
        result = repo.lookup_by_id("000000001")
        assert result is not None
        assert result.cust_first_name == "Jane"


# ===================================================================
# TransactionRepository
# ===================================================================

class TestInMemoryTransactionRepository:
    """Tests for InMemoryTransactionRepository."""

    def test_read_not_found(self) -> None:
        repo = InMemoryTransactionRepository()
        assert repo.read_by_id("0000000000000001") is None

    def test_write_and_read(self) -> None:
        repo = InMemoryTransactionRepository()
        txn = TransactionRecord(tran_id="0000000000000001", tran_amt=50.0)
        assert repo.write(txn) is True
        result = repo.read_by_id("0000000000000001")
        assert result is not None
        assert result.tran_amt == 50.0

    def test_write_duplicate(self) -> None:
        repo = InMemoryTransactionRepository()
        txn = TransactionRecord(tran_id="0000000000000001")
        repo.write(txn)
        assert repo.write(txn) is False

    def test_get_max_id_empty(self) -> None:
        repo = InMemoryTransactionRepository()
        assert repo.get_max_id() == 0

    def test_get_max_id(self) -> None:
        repo = InMemoryTransactionRepository()
        repo.seed(TransactionRecord(tran_id="0000000000000005"))
        repo.seed(TransactionRecord(tran_id="0000000000000010"))
        repo.seed(TransactionRecord(tran_id="0000000000000003"))
        assert repo.get_max_id() == 10

    def test_get_last_transaction_empty(self) -> None:
        repo = InMemoryTransactionRepository()
        assert repo.get_last_transaction() is None

    def test_get_last_transaction(self) -> None:
        repo = InMemoryTransactionRepository()
        repo.seed(TransactionRecord(tran_id="0000000000000005", tran_amt=5.0))
        repo.seed(TransactionRecord(tran_id="0000000000000010", tran_amt=10.0))
        last = repo.get_last_transaction()
        assert last is not None
        assert last.tran_id == "0000000000000010"
        assert last.tran_amt == 10.0

    def test_list_by_card(self) -> None:
        repo = InMemoryTransactionRepository()
        repo.seed(TransactionRecord(tran_id="0000000000000001", tran_card_num="CARD1"))
        repo.seed(TransactionRecord(tran_id="0000000000000002", tran_card_num="CARD1"))
        repo.seed(TransactionRecord(tran_id="0000000000000003", tran_card_num="CARD2"))
        result = repo.list_by_card("CARD1")
        assert len(result) == 2

    def test_list_by_account(self) -> None:
        repo = InMemoryTransactionRepository()
        repo.seed(TransactionRecord(tran_id="0000000000000001", tran_card_num="CARD1"))
        repo.seed(TransactionRecord(tran_id="0000000000000002", tran_card_num="CARD2"))
        repo.seed(TransactionRecord(tran_id="0000000000000003", tran_card_num="CARD3"))
        result = repo.list_by_account("ACCT1", ["CARD1", "CARD2"])
        assert len(result) == 2


# ===================================================================
# DailyTransactionRepository
# ===================================================================

class TestInMemoryDailyTransactionRepository:
    """Tests for InMemoryDailyTransactionRepository."""

    def test_read_all_empty(self) -> None:
        repo = InMemoryDailyTransactionRepository()
        assert repo.read_all() == []

    def test_seed_and_read_all(self) -> None:
        repo = InMemoryDailyTransactionRepository()
        repo.seed(DailyTransactionRecord(dalytran_id="0000000000000001"))
        repo.seed(DailyTransactionRecord(dalytran_id="0000000000000002"))
        result = repo.read_all()
        assert len(result) == 2
        assert result[0].dalytran_id == "0000000000000001"


# ===================================================================
# TranCatBalRepository
# ===================================================================

class TestInMemoryTranCatBalRepository:
    """Tests for InMemoryTranCatBalRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryTranCatBalRepository()
        assert repo.lookup("00000000001", "SA", "5001") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryTranCatBalRepository()
        rec = TranCatBalRecord(
            trancat_acct_id="00000000001",
            trancat_type_cd="SA",
            trancat_cd="5001",
            tran_cat_bal=100.0,
        )
        repo.seed(rec)
        result = repo.lookup("00000000001", "SA", "5001")
        assert result is not None
        assert result.tran_cat_bal == 100.0

    def test_update_existing(self) -> None:
        repo = InMemoryTranCatBalRepository()
        rec = TranCatBalRecord(
            trancat_acct_id="00000000001",
            trancat_type_cd="SA",
            trancat_cd="5001",
            tran_cat_bal=100.0,
        )
        repo.seed(rec)
        updated = TranCatBalRecord(
            trancat_acct_id="00000000001",
            trancat_type_cd="SA",
            trancat_cd="5001",
            tran_cat_bal=200.0,
        )
        assert repo.update(updated) is True
        result = repo.lookup("00000000001", "SA", "5001")
        assert result is not None
        assert result.tran_cat_bal == 200.0

    def test_update_not_found(self) -> None:
        repo = InMemoryTranCatBalRepository()
        rec = TranCatBalRecord(
            trancat_acct_id="00000000099",
            trancat_type_cd="XX",
            trancat_cd="9999",
        )
        assert repo.update(rec) is False


# ===================================================================
# DisclosureGroupRepository
# ===================================================================

class TestInMemoryDisclosureGroupRepository:
    """Tests for InMemoryDisclosureGroupRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryDisclosureGroupRepository()
        assert repo.lookup("GRP001", "SA", "5001") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryDisclosureGroupRepository()
        rec = DisclosureGroupRecord(
            dis_acct_group_id="GRP001",
            dis_tran_type_cd="SA",
            dis_tran_cat_cd="5001",
            dis_int_rate=18.99,
        )
        repo.seed(rec)
        result = repo.lookup("GRP001", "SA", "5001")
        assert result is not None
        assert result.dis_int_rate == 18.99


# ===================================================================
# TransactionTypeRepository
# ===================================================================

class TestInMemoryTransactionTypeRepository:
    """Tests for InMemoryTransactionTypeRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryTransactionTypeRepository()
        assert repo.lookup("ZZ") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryTransactionTypeRepository()
        rec = TransactionTypeRecord(tran_type="SA", tran_type_desc="Sale")
        repo.seed(rec)
        result = repo.lookup("SA")
        assert result is not None
        assert result.tran_type_desc == "Sale"


# ===================================================================
# TransactionCategoryRepository
# ===================================================================

class TestInMemoryTransactionCategoryRepository:
    """Tests for InMemoryTransactionCategoryRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryTransactionCategoryRepository()
        assert repo.lookup("ZZ", "9999") is None

    def test_seed_and_lookup(self) -> None:
        repo = InMemoryTransactionCategoryRepository()
        rec = TransactionCategoryRecord(
            tran_type_cd="SA",
            tran_cat_cd="5001",
            tran_cat_type_desc="Retail Sale",
        )
        repo.seed(rec)
        result = repo.lookup("SA", "5001")
        assert result is not None
        assert result.tran_cat_type_desc == "Retail Sale"


# ===================================================================
# UserSecurityRepository
# ===================================================================

class TestInMemoryUserSecurityRepository:
    """Tests for InMemoryUserSecurityRepository."""

    def test_lookup_not_found(self) -> None:
        repo = InMemoryUserSecurityRepository()
        assert repo.lookup("NOUSER") is None

    def test_add_and_lookup(self) -> None:
        repo = InMemoryUserSecurityRepository()
        user = UserSecurityRecord(
            sec_usr_id="ADMIN001",
            sec_usr_fname="Admin",
            sec_usr_lname="User",
            sec_usr_pwd="pass1234",
            sec_usr_type="A",
        )
        assert repo.add(user) is True
        result = repo.lookup("ADMIN001")
        assert result is not None
        assert result.sec_usr_fname == "Admin"

    def test_add_duplicate(self) -> None:
        repo = InMemoryUserSecurityRepository()
        user = UserSecurityRecord(sec_usr_id="ADMIN001")
        repo.add(user)
        assert repo.add(user) is False

    def test_update_existing(self) -> None:
        repo = InMemoryUserSecurityRepository()
        user = UserSecurityRecord(sec_usr_id="ADMIN001", sec_usr_fname="Admin")
        repo.add(user)
        updated = UserSecurityRecord(sec_usr_id="ADMIN001", sec_usr_fname="NewAdmin")
        assert repo.update(updated) is True
        result = repo.lookup("ADMIN001")
        assert result is not None
        assert result.sec_usr_fname == "NewAdmin"

    def test_update_not_found(self) -> None:
        repo = InMemoryUserSecurityRepository()
        user = UserSecurityRecord(sec_usr_id="NOUSER")
        assert repo.update(user) is False

    def test_delete_existing(self) -> None:
        repo = InMemoryUserSecurityRepository()
        user = UserSecurityRecord(sec_usr_id="ADMIN001")
        repo.add(user)
        assert repo.delete("ADMIN001") is True
        assert repo.lookup("ADMIN001") is None

    def test_delete_not_found(self) -> None:
        repo = InMemoryUserSecurityRepository()
        assert repo.delete("NOUSER") is False

    def test_list_all_empty(self) -> None:
        repo = InMemoryUserSecurityRepository()
        assert repo.list_all() == []

    def test_list_all(self) -> None:
        repo = InMemoryUserSecurityRepository()
        repo.add(UserSecurityRecord(sec_usr_id="USER001"))
        repo.add(UserSecurityRecord(sec_usr_id="USER002"))
        repo.add(UserSecurityRecord(sec_usr_id="USER003"))
        assert len(repo.list_all()) == 3

    def test_seed(self) -> None:
        repo = InMemoryUserSecurityRepository()
        user = UserSecurityRecord(sec_usr_id="SEEDED01")
        repo.seed(user)
        assert repo.lookup("SEEDED01") is not None
