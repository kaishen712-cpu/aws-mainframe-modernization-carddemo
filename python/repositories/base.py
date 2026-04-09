"""
Abstract repository interfaces for CardDemo data access.

Each interface mirrors the VSAM file operations used by the COBOL
programs (READ, WRITE, REWRITE, STARTBR/READNEXT, DELETE).  Concrete
implementations may use in-memory dicts, a SQL database, flat files, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

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


class AccountRepository(ABC):
    """Data-access interface for Account records (ACCTDAT VSAM file)."""

    @abstractmethod
    def lookup_by_id(self, acct_id: str) -> Optional[AccountRecord]:
        """Return an account by its 11-digit ID, or None if not found."""

    @abstractmethod
    def update(self, record: AccountRecord) -> bool:
        """Update an existing account record. Return True on success."""

    @abstractmethod
    def list_all(self) -> List[AccountRecord]:
        """Return all account records."""


class CardRepository(ABC):
    """Data-access interface for Card records (CARDDAT VSAM file)."""

    @abstractmethod
    def lookup_by_card_num(self, card_num: str) -> Optional[CardRecord]:
        """Return a card by its 16-character number, or None."""

    @abstractmethod
    def list_by_account(self, acct_id: str) -> List[CardRecord]:
        """Return all cards associated with the given account ID."""


class CardXrefRepository(ABC):
    """Data-access interface for Card cross-reference (CARDXREF VSAM file)."""

    @abstractmethod
    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        """Look up a cross-reference by card number (primary key)."""

    @abstractmethod
    def lookup_by_acct_id(self, acct_id: str) -> Optional[CardXrefRecord]:
        """Look up a cross-reference by account ID (alternate index)."""


class CustomerRepository(ABC):
    """Data-access interface for Customer records (CUSTDAT VSAM file)."""

    @abstractmethod
    def lookup_by_id(self, cust_id: str) -> Optional[CustomerRecord]:
        """Return a customer by its 9-digit ID, or None."""


class TransactionRepository(ABC):
    """Data-access interface for Transaction records (TRANSACT VSAM file)."""

    @abstractmethod
    def read_by_id(self, tran_id: str) -> Optional[TransactionRecord]:
        """Read a transaction by its 16-character ID."""

    @abstractmethod
    def write(self, record: TransactionRecord) -> bool:
        """Write a new transaction. Return False if duplicate key."""

    @abstractmethod
    def get_max_id(self) -> int:
        """Return the highest transaction ID as an integer (0 if empty)."""

    @abstractmethod
    def get_last_transaction(self) -> Optional[TransactionRecord]:
        """Return the transaction with the highest ID, or None."""

    @abstractmethod
    def list_by_card(self, card_num: str) -> List[TransactionRecord]:
        """Return all transactions for the given card number."""

    @abstractmethod
    def list_by_account(self, acct_id: str, card_nums: List[str]) -> List[TransactionRecord]:
        """Return all transactions for cards belonging to the account."""


class DailyTransactionRepository(ABC):
    """Data-access interface for Daily Transaction file (DALYTRAN)."""

    @abstractmethod
    def read_all(self) -> List[DailyTransactionRecord]:
        """Read all daily transaction records (sequential file)."""


class TranCatBalRepository(ABC):
    """Data-access interface for Transaction Category Balance (TCATBALF)."""

    @abstractmethod
    def lookup(
        self, acct_id: str, type_cd: str, cat_cd: str
    ) -> Optional[TranCatBalRecord]:
        """Look up a category balance by composite key."""

    @abstractmethod
    def update(self, record: TranCatBalRecord) -> bool:
        """Update an existing category balance record."""


class DisclosureGroupRepository(ABC):
    """Data-access interface for Disclosure Group records (DISCGRP)."""

    @abstractmethod
    def lookup(
        self, group_id: str, type_cd: str, cat_cd: str
    ) -> Optional[DisclosureGroupRecord]:
        """Look up a disclosure/interest rate by composite key."""


class TransactionTypeRepository(ABC):
    """Data-access interface for Transaction Type records (TRANTYPE)."""

    @abstractmethod
    def lookup(self, tran_type: str) -> Optional[TransactionTypeRecord]:
        """Look up a transaction type by its 2-character code."""


class TransactionCategoryRepository(ABC):
    """Data-access interface for Transaction Category records (TRANCATG)."""

    @abstractmethod
    def lookup(self, type_cd: str, cat_cd: str) -> Optional[TransactionCategoryRecord]:
        """Look up a category by type code + category code."""


class UserSecurityRepository(ABC):
    """Data-access interface for User Security records (USRSEC)."""

    @abstractmethod
    def lookup(self, user_id: str) -> Optional[UserSecurityRecord]:
        """Look up a user by their 8-character ID."""

    @abstractmethod
    def add(self, record: UserSecurityRecord) -> bool:
        """Add a new user. Return False if the ID already exists."""

    @abstractmethod
    def update(self, record: UserSecurityRecord) -> bool:
        """Update an existing user. Return False if not found."""

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete a user by ID. Return False if not found."""

    @abstractmethod
    def list_all(self) -> List[UserSecurityRecord]:
        """Return all user security records."""
