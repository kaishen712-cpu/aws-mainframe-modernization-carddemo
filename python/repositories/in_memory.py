"""
In-memory implementations of all CardDemo repository interfaces.

These are backed by plain Python dicts and lists, suitable for unit
testing and rapid prototyping without any external data store.
"""

from __future__ import annotations

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
from python.repositories.base import (
    AccountRepository,
    CardRepository,
    CardXrefRepository,
    CustomerRepository,
    DailyTransactionRepository,
    DisclosureGroupRepository,
    TranCatBalRepository,
    TransactionCategoryRepository,
    TransactionRepository,
    TransactionTypeRepository,
    UserSecurityRepository,
)


class InMemoryAccountRepository(AccountRepository):
    """In-memory account store keyed by ACCT-ID."""

    def __init__(self) -> None:
        self._store: dict[str, AccountRecord] = {}

    def seed(self, record: AccountRecord) -> None:
        """Add a record for test setup."""
        self._store[record.acct_id] = record

    def lookup_by_id(self, acct_id: str) -> AccountRecord | None:
        """Return an account by its 11-digit ID, or None if not found."""
        return self._store.get(acct_id)

    def update(self, record: AccountRecord) -> bool:
        """Update an existing account record. Return True on success."""
        if record.acct_id not in self._store:
            return False
        self._store[record.acct_id] = record
        return True

    def list_all(self) -> list[AccountRecord]:
        """Return all account records."""
        return list(self._store.values())


class InMemoryCardRepository(CardRepository):
    """In-memory card store keyed by CARD-NUM."""

    def __init__(self) -> None:
        self._store: dict[str, CardRecord] = {}

    def seed(self, record: CardRecord) -> None:
        """Add a record for test setup."""
        self._store[record.card_num] = record

    def lookup_by_card_num(self, card_num: str) -> CardRecord | None:
        """Return a card by its 16-character number, or None."""
        return self._store.get(card_num)

    def list_by_account(self, acct_id: str) -> list[CardRecord]:
        """Return all cards associated with the given account ID."""
        return [c for c in self._store.values() if c.card_acct_id == acct_id]


class InMemoryCardXrefRepository(CardXrefRepository):
    """In-memory card cross-reference store."""

    def __init__(self) -> None:
        self._by_card: dict[str, CardXrefRecord] = {}
        self._by_acct: dict[str, CardXrefRecord] = {}

    def seed(self, record: CardXrefRecord) -> None:
        """Add a record for test setup (indexes both keys)."""
        self._by_card[record.xref_card_num] = record
        self._by_acct[record.xref_acct_id] = record

    def lookup_by_card_num(self, card_num: str) -> CardXrefRecord | None:
        """Look up a cross-reference by card number (primary key)."""
        return self._by_card.get(card_num)

    def lookup_by_acct_id(self, acct_id: str) -> CardXrefRecord | None:
        """Look up a cross-reference by account ID (alternate index)."""
        return self._by_acct.get(acct_id)


class InMemoryCustomerRepository(CustomerRepository):
    """In-memory customer store keyed by CUST-ID."""

    def __init__(self) -> None:
        self._store: dict[str, CustomerRecord] = {}

    def seed(self, record: CustomerRecord) -> None:
        """Add a record for test setup."""
        self._store[record.cust_id] = record

    def lookup_by_id(self, cust_id: str) -> CustomerRecord | None:
        """Return a customer by its 9-digit ID, or None."""
        return self._store.get(cust_id)


class InMemoryTransactionRepository(TransactionRepository):
    """In-memory transaction store keyed by TRAN-ID."""

    def __init__(self) -> None:
        self._store: dict[str, TransactionRecord] = {}

    def seed(self, record: TransactionRecord) -> None:
        """Add a record for test setup."""
        self._store[record.tran_id] = record

    def read_by_id(self, tran_id: str) -> TransactionRecord | None:
        """Read a transaction by its 16-character ID."""
        return self._store.get(tran_id)

    def write(self, record: TransactionRecord) -> bool:
        """Write a new transaction. Return False if duplicate key."""
        if record.tran_id in self._store:
            return False
        self._store[record.tran_id] = record
        return True

    def get_max_id(self) -> int:
        """Return the highest transaction ID as an integer (0 if empty)."""
        if not self._store:
            return 0
        return max(int(tid) for tid in self._store)

    def get_last_transaction(self) -> TransactionRecord | None:
        """Return the transaction with the highest ID, or None."""
        if not self._store:
            return None
        max_key = max(self._store.keys(), key=lambda k: int(k))
        return self._store[max_key]

    def list_by_card(self, card_num: str) -> list[TransactionRecord]:
        """Return all transactions for the given card number."""
        return [t for t in self._store.values() if t.tran_card_num == card_num]

    def list_by_account(
        self, acct_id: str, card_nums: list[str]
    ) -> list[TransactionRecord]:
        """Return all transactions for cards belonging to the account."""
        card_set = set(card_nums)
        return [t for t in self._store.values() if t.tran_card_num in card_set]


class InMemoryDailyTransactionRepository(DailyTransactionRepository):
    """In-memory daily transaction store (sequential read)."""

    def __init__(self) -> None:
        self._records: list[DailyTransactionRecord] = []

    def seed(self, record: DailyTransactionRecord) -> None:
        """Append a record for test setup."""
        self._records.append(record)

    def read_all(self) -> list[DailyTransactionRecord]:
        """Read all daily transaction records (sequential file)."""
        return list(self._records)


class InMemoryTranCatBalRepository(TranCatBalRepository):
    """In-memory transaction category balance store."""

    def __init__(self) -> None:
        self._store: dict[str, TranCatBalRecord] = {}

    @staticmethod
    def _key(acct_id: str, type_cd: str, cat_cd: str) -> str:
        return f"{acct_id}|{type_cd}|{cat_cd}"

    def seed(self, record: TranCatBalRecord) -> None:
        """Add a record for test setup."""
        key = self._key(record.trancat_acct_id, record.trancat_type_cd, record.trancat_cd)
        self._store[key] = record

    def lookup(
        self, acct_id: str, type_cd: str, cat_cd: str
    ) -> TranCatBalRecord | None:
        """Look up a category balance by composite key."""
        return self._store.get(self._key(acct_id, type_cd, cat_cd))

    def update(self, record: TranCatBalRecord) -> bool:
        """Update an existing category balance record."""
        key = self._key(record.trancat_acct_id, record.trancat_type_cd, record.trancat_cd)
        if key not in self._store:
            return False
        self._store[key] = record
        return True


class InMemoryDisclosureGroupRepository(DisclosureGroupRepository):
    """In-memory disclosure group store."""

    def __init__(self) -> None:
        self._store: dict[str, DisclosureGroupRecord] = {}

    @staticmethod
    def _key(group_id: str, type_cd: str, cat_cd: str) -> str:
        return f"{group_id}|{type_cd}|{cat_cd}"

    def seed(self, record: DisclosureGroupRecord) -> None:
        """Add a record for test setup."""
        key = self._key(record.dis_acct_group_id, record.dis_tran_type_cd, record.dis_tran_cat_cd)
        self._store[key] = record

    def lookup(
        self, group_id: str, type_cd: str, cat_cd: str
    ) -> DisclosureGroupRecord | None:
        """Look up a disclosure/interest rate by composite key."""
        return self._store.get(self._key(group_id, type_cd, cat_cd))


class InMemoryTransactionTypeRepository(TransactionTypeRepository):
    """In-memory transaction type store keyed by TRAN-TYPE."""

    def __init__(self) -> None:
        self._store: dict[str, TransactionTypeRecord] = {}

    def seed(self, record: TransactionTypeRecord) -> None:
        """Add a record for test setup."""
        self._store[record.tran_type] = record

    def lookup(self, tran_type: str) -> TransactionTypeRecord | None:
        """Look up a transaction type by its 2-character code."""
        return self._store.get(tran_type)


class InMemoryTransactionCategoryRepository(TransactionCategoryRepository):
    """In-memory transaction category store."""

    def __init__(self) -> None:
        self._store: dict[str, TransactionCategoryRecord] = {}

    @staticmethod
    def _key(type_cd: str, cat_cd: str) -> str:
        return f"{type_cd}|{cat_cd}"

    def seed(self, record: TransactionCategoryRecord) -> None:
        """Add a record for test setup."""
        self._store[self._key(record.tran_type_cd, record.tran_cat_cd)] = record

    def lookup(
        self, type_cd: str, cat_cd: str
    ) -> TransactionCategoryRecord | None:
        """Look up a category by type code + category code."""
        return self._store.get(self._key(type_cd, cat_cd))


class InMemoryUserSecurityRepository(UserSecurityRepository):
    """In-memory user security store keyed by SEC-USR-ID."""

    def __init__(self) -> None:
        self._store: dict[str, UserSecurityRecord] = {}

    def seed(self, record: UserSecurityRecord) -> None:
        """Add a record for test setup."""
        self._store[record.sec_usr_id] = record

    def lookup(self, user_id: str) -> UserSecurityRecord | None:
        """Look up a user by their 8-character ID."""
        return self._store.get(user_id)

    def add(self, record: UserSecurityRecord) -> bool:
        """Add a new user. Return False if the ID already exists."""
        if record.sec_usr_id in self._store:
            return False
        self._store[record.sec_usr_id] = record
        return True

    def update(self, record: UserSecurityRecord) -> bool:
        """Update an existing user. Return False if not found."""
        if record.sec_usr_id not in self._store:
            return False
        self._store[record.sec_usr_id] = record
        return True

    def delete(self, user_id: str) -> bool:
        """Delete a user by ID. Return False if not found."""
        if user_id not in self._store:
            return False
        del self._store[user_id]
        return True

    def list_all(self) -> list[UserSecurityRecord]:
        """Return all user security records."""
        return list(self._store.values())
