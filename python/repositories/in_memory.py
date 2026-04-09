"""
In-memory implementations of all CardDemo repository interfaces.

These are backed by plain Python dicts and lists, suitable for unit
testing and rapid prototyping without any external data store.
"""

from __future__ import annotations

from typing import Dict, List, Optional

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
        self._store: Dict[str, AccountRecord] = {}

    def seed(self, record: AccountRecord) -> None:
        """Add a record for test setup."""
        self._store[record.acct_id] = record

    def lookup_by_id(self, acct_id: str) -> Optional[AccountRecord]:
        return self._store.get(acct_id)

    def update(self, record: AccountRecord) -> bool:
        if record.acct_id not in self._store:
            return False
        self._store[record.acct_id] = record
        return True

    def list_all(self) -> List[AccountRecord]:
        return list(self._store.values())


class InMemoryCardRepository(CardRepository):
    """In-memory card store keyed by CARD-NUM."""

    def __init__(self) -> None:
        self._store: Dict[str, CardRecord] = {}

    def seed(self, record: CardRecord) -> None:
        """Add a record for test setup."""
        self._store[record.card_num] = record

    def lookup_by_card_num(self, card_num: str) -> Optional[CardRecord]:
        return self._store.get(card_num)

    def list_by_account(self, acct_id: str) -> List[CardRecord]:
        return [c for c in self._store.values() if c.card_acct_id == acct_id]


class InMemoryCardXrefRepository(CardXrefRepository):
    """In-memory card cross-reference store."""

    def __init__(self) -> None:
        self._by_card: Dict[str, CardXrefRecord] = {}
        self._by_acct: Dict[str, CardXrefRecord] = {}

    def seed(self, record: CardXrefRecord) -> None:
        """Add a record for test setup (indexes both keys)."""
        self._by_card[record.xref_card_num] = record
        self._by_acct[record.xref_acct_id] = record

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        return self._by_card.get(card_num)

    def lookup_by_acct_id(self, acct_id: str) -> Optional[CardXrefRecord]:
        return self._by_acct.get(acct_id)


class InMemoryCustomerRepository(CustomerRepository):
    """In-memory customer store keyed by CUST-ID."""

    def __init__(self) -> None:
        self._store: Dict[str, CustomerRecord] = {}

    def seed(self, record: CustomerRecord) -> None:
        """Add a record for test setup."""
        self._store[record.cust_id] = record

    def lookup_by_id(self, cust_id: str) -> Optional[CustomerRecord]:
        return self._store.get(cust_id)


class InMemoryTransactionRepository(TransactionRepository):
    """In-memory transaction store keyed by TRAN-ID."""

    def __init__(self) -> None:
        self._store: Dict[str, TransactionRecord] = {}

    def seed(self, record: TransactionRecord) -> None:
        """Add a record for test setup."""
        self._store[record.tran_id] = record

    def read_by_id(self, tran_id: str) -> Optional[TransactionRecord]:
        return self._store.get(tran_id)

    def write(self, record: TransactionRecord) -> bool:
        if record.tran_id in self._store:
            return False
        self._store[record.tran_id] = record
        return True

    def get_max_id(self) -> int:
        if not self._store:
            return 0
        return max(int(tid) for tid in self._store)

    def get_last_transaction(self) -> Optional[TransactionRecord]:
        if not self._store:
            return None
        max_key = max(self._store.keys(), key=lambda k: int(k))
        return self._store[max_key]

    def list_by_card(self, card_num: str) -> List[TransactionRecord]:
        return [t for t in self._store.values() if t.tran_card_num == card_num]

    def list_by_account(
        self, acct_id: str, card_nums: List[str]
    ) -> List[TransactionRecord]:
        card_set = set(card_nums)
        return [t for t in self._store.values() if t.tran_card_num in card_set]


class InMemoryDailyTransactionRepository(DailyTransactionRepository):
    """In-memory daily transaction store (sequential read)."""

    def __init__(self) -> None:
        self._records: List[DailyTransactionRecord] = []

    def seed(self, record: DailyTransactionRecord) -> None:
        """Append a record for test setup."""
        self._records.append(record)

    def read_all(self) -> List[DailyTransactionRecord]:
        return list(self._records)


class InMemoryTranCatBalRepository(TranCatBalRepository):
    """In-memory transaction category balance store."""

    def __init__(self) -> None:
        self._store: Dict[str, TranCatBalRecord] = {}

    @staticmethod
    def _key(acct_id: str, type_cd: str, cat_cd: str) -> str:
        return f"{acct_id}|{type_cd}|{cat_cd}"

    def seed(self, record: TranCatBalRecord) -> None:
        """Add a record for test setup."""
        key = self._key(record.trancat_acct_id, record.trancat_type_cd, record.trancat_cd)
        self._store[key] = record

    def lookup(
        self, acct_id: str, type_cd: str, cat_cd: str
    ) -> Optional[TranCatBalRecord]:
        return self._store.get(self._key(acct_id, type_cd, cat_cd))

    def update(self, record: TranCatBalRecord) -> bool:
        key = self._key(record.trancat_acct_id, record.trancat_type_cd, record.trancat_cd)
        if key not in self._store:
            return False
        self._store[key] = record
        return True


class InMemoryDisclosureGroupRepository(DisclosureGroupRepository):
    """In-memory disclosure group store."""

    def __init__(self) -> None:
        self._store: Dict[str, DisclosureGroupRecord] = {}

    @staticmethod
    def _key(group_id: str, type_cd: str, cat_cd: str) -> str:
        return f"{group_id}|{type_cd}|{cat_cd}"

    def seed(self, record: DisclosureGroupRecord) -> None:
        """Add a record for test setup."""
        key = self._key(record.dis_acct_group_id, record.dis_tran_type_cd, record.dis_tran_cat_cd)
        self._store[key] = record

    def lookup(
        self, group_id: str, type_cd: str, cat_cd: str
    ) -> Optional[DisclosureGroupRecord]:
        return self._store.get(self._key(group_id, type_cd, cat_cd))


class InMemoryTransactionTypeRepository(TransactionTypeRepository):
    """In-memory transaction type store keyed by TRAN-TYPE."""

    def __init__(self) -> None:
        self._store: Dict[str, TransactionTypeRecord] = {}

    def seed(self, record: TransactionTypeRecord) -> None:
        """Add a record for test setup."""
        self._store[record.tran_type] = record

    def lookup(self, tran_type: str) -> Optional[TransactionTypeRecord]:
        return self._store.get(tran_type)


class InMemoryTransactionCategoryRepository(TransactionCategoryRepository):
    """In-memory transaction category store."""

    def __init__(self) -> None:
        self._store: Dict[str, TransactionCategoryRecord] = {}

    @staticmethod
    def _key(type_cd: str, cat_cd: str) -> str:
        return f"{type_cd}|{cat_cd}"

    def seed(self, record: TransactionCategoryRecord) -> None:
        """Add a record for test setup."""
        self._store[self._key(record.tran_type_cd, record.tran_cat_cd)] = record

    def lookup(
        self, type_cd: str, cat_cd: str
    ) -> Optional[TransactionCategoryRecord]:
        return self._store.get(self._key(type_cd, cat_cd))


class InMemoryUserSecurityRepository(UserSecurityRepository):
    """In-memory user security store keyed by SEC-USR-ID."""

    def __init__(self) -> None:
        self._store: Dict[str, UserSecurityRecord] = {}

    def seed(self, record: UserSecurityRecord) -> None:
        """Add a record for test setup."""
        self._store[record.sec_usr_id] = record

    def lookup(self, user_id: str) -> Optional[UserSecurityRecord]:
        return self._store.get(user_id)

    def add(self, record: UserSecurityRecord) -> bool:
        if record.sec_usr_id in self._store:
            return False
        self._store[record.sec_usr_id] = record
        return True

    def update(self, record: UserSecurityRecord) -> bool:
        if record.sec_usr_id not in self._store:
            return False
        self._store[record.sec_usr_id] = record
        return True

    def delete(self, user_id: str) -> bool:
        if user_id not in self._store:
            return False
        del self._store[user_id]
        return True

    def list_all(self) -> List[UserSecurityRecord]:
        return list(self._store.values())
