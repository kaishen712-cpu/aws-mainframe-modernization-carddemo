"""
User Security Repository — abstract interface and in-memory implementation.

This module defines the data-access layer for the USRSEC VSAM file used by
the CardDemo admin user-management programs (COUSR00C–COUSR03C).

The abstract ``UserSecurityRepository`` mirrors the CICS file operations
(READ, WRITE, REWRITE, DELETE, STARTBR/READNEXT/READPREV/ENDBR) and the
concrete ``InMemoryUserSecurityRepository`` provides a dict-backed store
suitable for unit testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structure  (from copybook CSUSR01Y — 80 bytes)
# ---------------------------------------------------------------------------

@dataclass
class UserSecurityRecord:
    """
    User security record layout (CSUSR01Y — 80 bytes).

    Fields mirror the COBOL copybook:
        SEC-USR-ID      PIC X(08)   — primary key
        SEC-USR-FNAME   PIC X(20)
        SEC-USR-LNAME   PIC X(20)
        SEC-USR-PWD     PIC X(08)
        SEC-USR-TYPE    PIC X(01)   — 'A' (admin) or 'U' (regular)
        SEC-USR-FILLER  PIC X(23)
    """
    user_id: str = ""
    first_name: str = ""
    last_name: str = ""
    password: str = ""
    user_type: str = ""       # 'A' or 'U'
    filler: str = ""


# ---------------------------------------------------------------------------
# Page of users returned by browse operations
# ---------------------------------------------------------------------------

@dataclass
class UserPage:
    """A single page of user records returned by a browse operation."""
    users: list[UserSecurityRecord] = field(default_factory=list)
    has_next: bool = False
    has_prev: bool = False
    page_num: int = 0


# ---------------------------------------------------------------------------
# Abstract repository interface
# ---------------------------------------------------------------------------

class UserSecurityRepository:
    """
    Abstract interface for USRSEC file operations.

    In the original COBOL programs these are CICS READ / WRITE / REWRITE /
    DELETE / STARTBR / READNEXT / READPREV / ENDBR operations against a
    VSAM KSDS file keyed by SEC-USR-ID.
    """

    def lookup_user(self, user_id: str) -> Optional[UserSecurityRecord]:
        """
        Read a single user record by primary key.

        Corresponds to CICS READ on USRSEC with RIDFLD(SEC-USR-ID).
        Returns None if the user is not found (NOTFND response).
        """
        raise NotImplementedError

    def add_user(self, record: UserSecurityRecord) -> bool:
        """
        Write a new user record.

        Corresponds to CICS WRITE to the USRSEC file.
        Returns True on success, False if a duplicate key exists
        (DUPKEY / DUPREC response).
        """
        raise NotImplementedError

    def update_user(self, record: UserSecurityRecord) -> bool:
        """
        Rewrite (update) an existing user record.

        Corresponds to CICS READ-UPDATE followed by REWRITE on USRSEC.
        Returns True on success, False if the user is not found.
        """
        raise NotImplementedError

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user record by primary key.

        Corresponds to CICS READ-UPDATE followed by DELETE on USRSEC.
        Returns True on success, False if the user is not found.
        """
        raise NotImplementedError

    def list_users(self) -> list[UserSecurityRecord]:
        """
        Return all user records ordered by user_id.

        Convenience method used by higher-level logic.
        """
        raise NotImplementedError

    def browse_users_forward(
        self,
        start_user_id: str = "",
        page_size: int = 10,
    ) -> UserPage:
        """
        Browse users forward from *start_user_id* (inclusive).

        Corresponds to STARTBR + READNEXT loop in COUSR00C.
        Returns up to *page_size* records and a flag indicating whether
        more records exist beyond the page.
        """
        raise NotImplementedError

    def browse_users_backward(
        self,
        start_user_id: str = "",
        page_size: int = 10,
    ) -> UserPage:
        """
        Browse users backward from *start_user_id* (inclusive).

        Corresponds to STARTBR + READPREV loop in COUSR00C.
        Returns up to *page_size* records (in ascending order) and a flag
        indicating whether more records exist before the page.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryUserSecurityRepository(UserSecurityRepository):
    """Simple in-memory implementation backed by a sorted dict."""

    def __init__(self) -> None:
        self._users: dict[str, UserSecurityRecord] = {}

    # -- seed helper --------------------------------------------------------

    def seed(self, record: UserSecurityRecord) -> None:
        """Insert a record directly (for test setup)."""
        self._users[record.user_id] = record

    # -- interface ----------------------------------------------------------

    def lookup_user(self, user_id: str) -> Optional[UserSecurityRecord]:
        return self._users.get(user_id)

    def add_user(self, record: UserSecurityRecord) -> bool:
        if record.user_id in self._users:
            return False
        self._users[record.user_id] = record
        return True

    def update_user(self, record: UserSecurityRecord) -> bool:
        if record.user_id not in self._users:
            return False
        self._users[record.user_id] = record
        return True

    def delete_user(self, user_id: str) -> bool:
        if user_id not in self._users:
            return False
        del self._users[user_id]
        return True

    def list_users(self) -> list[UserSecurityRecord]:
        return [self._users[k] for k in sorted(self._users)]

    def browse_users_forward(
        self,
        start_user_id: str = "",
        page_size: int = 10,
    ) -> UserPage:
        all_ids = sorted(self._users)
        # Find starting index (>= start_user_id)
        start_idx = 0
        if start_user_id:
            for i, uid in enumerate(all_ids):
                if uid >= start_user_id:
                    start_idx = i
                    break
            else:
                # All IDs are less than start_user_id — no results
                return UserPage(users=[], has_next=False, has_prev=len(all_ids) > 0)

        page_ids = all_ids[start_idx: start_idx + page_size]
        users = [self._users[uid] for uid in page_ids]
        has_next = (start_idx + page_size) < len(all_ids)
        has_prev = start_idx > 0
        return UserPage(users=users, has_next=has_next, has_prev=has_prev)

    def browse_users_backward(
        self,
        start_user_id: str = "",
        page_size: int = 10,
    ) -> UserPage:
        all_ids = sorted(self._users)
        if not all_ids:
            return UserPage(users=[], has_next=False, has_prev=False)

        # Find ending index (<= start_user_id)
        end_idx = len(all_ids) - 1
        if start_user_id:
            found = False
            for i in range(len(all_ids) - 1, -1, -1):
                if all_ids[i] <= start_user_id:
                    end_idx = i
                    found = True
                    break
            if not found:
                return UserPage(users=[], has_next=len(all_ids) > 0, has_prev=False)

        start_idx = max(0, end_idx - page_size + 1)
        page_ids = all_ids[start_idx: end_idx + 1]
        users = [self._users[uid] for uid in page_ids]
        has_prev = start_idx > 0
        has_next = end_idx < len(all_ids) - 1
        return UserPage(users=users, has_next=has_next, has_prev=has_prev)
