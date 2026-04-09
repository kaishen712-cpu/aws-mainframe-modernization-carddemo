"""
CardDemo repository interfaces and implementations.

Provides abstract base classes (ABCs) defining data-access contracts
for each VSAM file, plus in-memory implementations for testing.
"""

from python.repositories.base import (
    AccountRepository,
    CardRepository,
    CardXrefRepository,
    CustomerRepository,
    TransactionRepository,
    DailyTransactionRepository,
    TranCatBalRepository,
    DisclosureGroupRepository,
    TransactionTypeRepository,
    TransactionCategoryRepository,
    UserSecurityRepository,
)

__all__ = [
    "AccountRepository",
    "CardRepository",
    "CardXrefRepository",
    "CustomerRepository",
    "TransactionRepository",
    "DailyTransactionRepository",
    "TranCatBalRepository",
    "DisclosureGroupRepository",
    "TransactionTypeRepository",
    "TransactionCategoryRepository",
    "UserSecurityRepository",
]
