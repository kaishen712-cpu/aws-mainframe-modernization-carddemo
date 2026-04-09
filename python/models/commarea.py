"""
CardDemo communication area (COMMAREA) dataclass.

Translated from COCOM01Y.cpy — the session state structure passed between
CICS programs via EXEC CICS RETURN TRANSID / XCTL.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CardDemoCommarea:
    """Communication area shared across CardDemo CICS programs (COCOM01Y.cpy).

    This structure carries session context — the signed-in user, the
    current and previous program/transaction, customer/account/card
    identifiers, and the last BMS map displayed.
    """

    # --- General info (CDEMO-GENERAL-INFO) ---
    cdemo_from_tranid: str = ""         # CDEMO-FROM-TRANID    PIC X(04)
    cdemo_from_program: str = ""        # CDEMO-FROM-PROGRAM   PIC X(08)
    cdemo_to_tranid: str = ""           # CDEMO-TO-TRANID      PIC X(04)
    cdemo_to_program: str = ""          # CDEMO-TO-PROGRAM     PIC X(08)
    cdemo_user_id: str = ""             # CDEMO-USER-ID        PIC X(08)
    cdemo_user_type: str = ""           # CDEMO-USER-TYPE      PIC X(01)
                                        #   'A' = Admin, 'U' = User
    cdemo_pgm_context: int = 0          # CDEMO-PGM-CONTEXT    PIC 9(01)
                                        #   0 = enter, 1 = re-enter

    # --- Customer info (CDEMO-CUSTOMER-INFO) ---
    cdemo_cust_id: str = ""             # CDEMO-CUST-ID        PIC 9(09)
    cdemo_cust_fname: str = ""          # CDEMO-CUST-FNAME     PIC X(25)
    cdemo_cust_mname: str = ""          # CDEMO-CUST-MNAME     PIC X(25)
    cdemo_cust_lname: str = ""          # CDEMO-CUST-LNAME     PIC X(25)

    # --- Account info (CDEMO-ACCOUNT-INFO) ---
    cdemo_acct_id: str = ""             # CDEMO-ACCT-ID        PIC 9(11)
    cdemo_acct_status: str = ""         # CDEMO-ACCT-STATUS    PIC X(01)

    # --- Card info (CDEMO-CARD-INFO) ---
    cdemo_card_num: str = ""            # CDEMO-CARD-NUM       PIC 9(16)

    # --- More info (CDEMO-MORE-INFO) ---
    cdemo_last_map: str = ""            # CDEMO-LAST-MAP       PIC X(7)
    cdemo_last_mapset: str = ""         # CDEMO-LAST-MAPSET    PIC X(7)

    @property
    def is_admin(self) -> bool:
        """Return True if the user type indicates an administrator."""
        return self.cdemo_user_type == "A"

    @property
    def is_user(self) -> bool:
        """Return True if the user type indicates a regular user."""
        return self.cdemo_user_type == "U"

    @property
    def is_program_enter(self) -> bool:
        """Return True when the program context is initial entry."""
        return self.cdemo_pgm_context == 0

    @property
    def is_program_reenter(self) -> bool:
        """Return True when the program context is re-entry."""
        return self.cdemo_pgm_context == 1
