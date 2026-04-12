"""
Business logic services for Transaction Management.

Refactored from python/cotrn02c.py — reuses existing translated code.
Original COBOL programs:
- COTRN00C.cbl — Transaction list (STARTBR/READNEXT)
- COTRN01C.cbl — Transaction detail view
- COTRN02C.cbl — Transaction add (full validation + write)
- COBIL00C.cbl — Bill payment processing

Follows SRP: views handle HTTP, services handle business logic.
All monetary calculations use Decimal (never float) per CPS 234.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

AMOUNT_PATTERN = re.compile(r"^[+\-]\d{8}\.\d{2}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Bill payment transaction type codes
# FLAGGED FOR HUMAN REVIEW: Hardcoded transaction type codes
BILL_PAY_TYPE_CD = "BP"
BILL_PAY_CAT_CD = "0001"
BILL_PAY_SOURCE = "ONLINE"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TransactionInput:
    """User-supplied fields from the Add Transaction screen.

    Reused from cotrn02c.py TransactionInput dataclass.
    Corresponds to COTRN2AI BMS map input fields.
    """

    acct_id: str = ""
    card_num: str = ""
    tran_type_cd: str = ""
    tran_cat_cd: str = ""
    tran_source: str = ""
    tran_desc: str = ""
    tran_amt: str = ""
    orig_date: str = ""
    proc_date: str = ""
    merchant_id: str = ""
    merchant_name: str = ""
    merchant_city: str = ""
    merchant_zip: str = ""
    confirm: str = ""


@dataclass
class ValidationResult:
    """Outcome of a validation step."""

    is_valid: bool = True
    error_message: str = ""
    error_field: str = ""


@dataclass
class AddTransactionResult:
    """Outcome of the add-transaction operation."""

    success: bool = False
    message: str = ""
    tran_id: str = ""


@dataclass
class BillPayResult:
    """Outcome of a bill payment operation."""

    success: bool = False
    message: str = ""
    tran_id: str = ""


# ---------------------------------------------------------------------------
# Transaction list service
# ---------------------------------------------------------------------------

def get_transaction_list(
    card_num: str = "",
    acct_id: str = "",
    tran_type_cd: str = "",
) -> QuerySet:
    """Return filtered transaction queryset.

    Translated from COTRN00C.cbl — 0000-MAIN / 9000-READ-DATA.

    Business rules:
    - Filter by card number, account ID, or transaction type.
    - Results ordered by transaction ID descending (most recent first).
    - CICS STARTBR/READNEXT replaced by Django queryset pagination.

    Args:
        card_num: Card number filter.
        acct_id: Account ID filter (looks up cards via xref).
        tran_type_cd: Transaction type code filter.

    Returns:
        Filtered queryset of Transaction objects.
    """
    from python.cards.models import CardXref
    from python.transactions.models import Transaction

    queryset = Transaction.objects.all()

    if card_num:
        queryset = queryset.filter(tran_card_num=card_num)
    elif acct_id:
        card_nums = CardXref.objects.filter(
            xref_acct_id=acct_id,
        ).values_list("xref_card_num", flat=True)
        queryset = queryset.filter(tran_card_num__in=card_nums)

    if tran_type_cd:
        queryset = queryset.filter(tran_type_cd=tran_type_cd)

    return queryset.order_by("-tran_id")


# ---------------------------------------------------------------------------
# Validation functions (refactored from cotrn02c.py)
# ---------------------------------------------------------------------------

def validate_key_fields(txn_input: TransactionInput) -> ValidationResult:
    """Validate key fields: account ID and/or card number.

    Refactored from cotrn02c.py validate_key_fields.
    Uses Django ORM instead of repository pattern.

    Business rules (from VALIDATE-INPUT-KEY-FIELDS):
    - At least one of account ID or card number must be provided.
    - If account ID is provided, must be numeric and exist in xref.
    - If card number is provided, must be numeric and exist in xref.
    """
    from python.cards.models import CardXref

    has_acct = txn_input.acct_id.strip() != ""
    has_card = txn_input.card_num.strip() != ""

    if has_acct:
        if not txn_input.acct_id.strip().isdigit():
            return ValidationResult(
                is_valid=False,
                error_message="Account ID must be Numeric...",
                error_field="acct_id",
            )
        normalised_acct = txn_input.acct_id.strip().zfill(11)
        txn_input.acct_id = normalised_acct

        try:
            xref = CardXref.objects.filter(
                xref_acct_id=normalised_acct,
            ).first()
        except Exception:
            xref = None

        if xref is None:
            return ValidationResult(
                is_valid=False,
                error_message="Account ID NOT found...",
                error_field="acct_id",
            )
        txn_input.card_num = xref.xref_card_num
        return ValidationResult(is_valid=True)

    if has_card:
        if not txn_input.card_num.strip().isdigit():
            return ValidationResult(
                is_valid=False,
                error_message="Card Number must be Numeric...",
                error_field="card_num",
            )
        normalised_card = txn_input.card_num.strip().zfill(16)
        txn_input.card_num = normalised_card

        try:
            xref = CardXref.objects.filter(
                xref_card_num=normalised_card,
            ).first()
        except Exception:
            xref = None

        if xref is None:
            return ValidationResult(
                is_valid=False,
                error_message="Card Number NOT found...",
                error_field="card_num",
            )
        txn_input.acct_id = xref.xref_acct_id
        return ValidationResult(is_valid=True)

    return ValidationResult(
        is_valid=False,
        error_message="Account or Card Number must be entered...",
        error_field="acct_id",
    )


def validate_data_fields(
    txn_input: TransactionInput,
) -> ValidationResult:
    """Validate all non-key data fields.

    Refactored from cotrn02c.py validate_data_fields.

    Business rules (from VALIDATE-INPUT-DATA-FIELDS):
    1. All fields must be non-empty.
    2. Type Code and Category Code must be numeric.
    3. Amount must match format +/-99999999.99.
    4. Dates must match YYYY-MM-DD and be valid calendar dates.
    5. Merchant ID must be numeric.
    """
    required_fields = [
        ("tran_type_cd", "Type CD can NOT be empty..."),
        ("tran_cat_cd", "Category CD can NOT be empty..."),
        ("tran_source", "Source can NOT be empty..."),
        ("tran_desc", "Description can NOT be empty..."),
        ("tran_amt", "Amount can NOT be empty..."),
        ("orig_date", "Orig Date can NOT be empty..."),
        ("proc_date", "Proc Date can NOT be empty..."),
        ("merchant_id", "Merchant ID can NOT be empty..."),
        ("merchant_name", "Merchant Name can NOT be empty..."),
        ("merchant_city", "Merchant City can NOT be empty..."),
        ("merchant_zip", "Merchant Zip can NOT be empty..."),
    ]

    for field_name, error_msg in required_fields:
        value = getattr(txn_input, field_name)
        if value.strip() == "":
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                error_field=field_name,
            )

    if not txn_input.tran_type_cd.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Type CD must be Numeric...",
            error_field="tran_type_cd",
        )

    if not txn_input.tran_cat_cd.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Category CD must be Numeric...",
            error_field="tran_cat_cd",
        )

    amt = txn_input.tran_amt.strip()
    if not AMOUNT_PATTERN.match(amt):
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Amount should be in format -99999999.99"
            ),
            error_field="tran_amt",
        )

    orig = txn_input.orig_date.strip()
    if not DATE_PATTERN.match(orig):
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Orig Date should be in format YYYY-MM-DD"
            ),
            error_field="orig_date",
        )
    if not _is_valid_calendar_date(orig):
        return ValidationResult(
            is_valid=False,
            error_message="Orig Date - Not a valid date...",
            error_field="orig_date",
        )

    proc = txn_input.proc_date.strip()
    if not DATE_PATTERN.match(proc):
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Proc Date should be in format YYYY-MM-DD"
            ),
            error_field="proc_date",
        )
    if not _is_valid_calendar_date(proc):
        return ValidationResult(
            is_valid=False,
            error_message="Proc Date - Not a valid date...",
            error_field="proc_date",
        )

    if not txn_input.merchant_id.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Merchant ID must be Numeric...",
            error_field="merchant_id",
        )

    return ValidationResult(is_valid=True)


def validate_confirmation(confirm_value: str) -> ValidationResult:
    """Check the confirmation flag.

    Refactored from cotrn02c.py validate_confirmation.

    Business rules (from PROCESS-ENTER-KEY):
    - 'Y' or 'y' means confirmed.
    - 'N', 'n', blank means not yet confirmed.
    - Anything else is invalid.
    """
    c = confirm_value.strip().upper()
    if c == "Y":
        return ValidationResult(is_valid=True)
    if c in ("N", ""):
        return ValidationResult(
            is_valid=False,
            error_message="Confirm to add this transaction...",
            error_field="confirm",
        )
    return ValidationResult(
        is_valid=False,
        error_message="Invalid value. Valid values are (Y/N)...",
        error_field="confirm",
    )


# ---------------------------------------------------------------------------
# Core transaction-add logic
# ---------------------------------------------------------------------------

def generate_transaction_id() -> str:
    """Generate the next transaction ID.

    Refactored from cotrn02c.py generate_transaction_id.
    Uses Django ORM instead of repository pattern.

    Business rule (from ADD-TRANSACTION):
    Browse to end of TRANSACT file, read last record, add 1.
    If file is empty, start from 1.
    """
    from python.transactions.models import Transaction

    last = Transaction.objects.order_by("-tran_id").first()
    if last is None:
        next_id = 1
    else:
        try:
            next_id = int(last.tran_id) + 1
        except (ValueError, TypeError):
            next_id = 1
    return str(next_id).zfill(16)


def add_transaction(
    txn_input: TransactionInput,
) -> AddTransactionResult:
    """Full add-transaction workflow: validate, generate ID, write.

    Refactored from cotrn02c.py add_transaction.
    Uses Django ORM instead of repository pattern.

    This is the top-level entry point that mirrors the COBOL
    PROCESS-ENTER-KEY paragraph when confirmation = 'Y'.
    """
    from python.transactions.models import Transaction

    key_result = validate_key_fields(txn_input)
    if not key_result.is_valid:
        return AddTransactionResult(
            success=False,
            message=key_result.error_message,
        )

    data_result = validate_data_fields(txn_input)
    if not data_result.is_valid:
        return AddTransactionResult(
            success=False,
            message=data_result.error_message,
        )

    confirm_result = validate_confirmation(txn_input.confirm)
    if not confirm_result.is_valid:
        return AddTransactionResult(
            success=False,
            message=confirm_result.error_message,
        )

    amt = _parse_amount(txn_input.tran_amt.strip())

    # Retry loop to handle race condition on transaction ID generation.
    # Two concurrent requests may generate the same ID; the unique
    # constraint rejects the duplicate and we retry with a fresh ID.
    max_retries = 3
    for attempt in range(max_retries):
        tran_id = generate_transaction_id()
        try:
            with transaction.atomic():
                Transaction.objects.create(
                    tran_id=tran_id,
                    tran_type_cd=txn_input.tran_type_cd.strip(),
                    tran_cat_cd=txn_input.tran_cat_cd.strip(),
                    tran_source=txn_input.tran_source.strip(),
                    tran_desc=txn_input.tran_desc.strip(),
                    tran_amt=amt,
                    tran_merchant_id=txn_input.merchant_id.strip(),
                    tran_merchant_name=txn_input.merchant_name.strip(),
                    tran_merchant_city=txn_input.merchant_city.strip(),
                    tran_merchant_zip=txn_input.merchant_zip.strip(),
                    tran_card_num=txn_input.card_num.strip(),
                    tran_orig_ts=txn_input.orig_date.strip(),
                    tran_proc_ts=txn_input.proc_date.strip(),
                )
            break
        except IntegrityError:
            if attempt == max_retries - 1:
                return AddTransactionResult(
                    success=False,
                    message="Tran ID already exist...",
                )
            continue
        except Exception:
            return AddTransactionResult(
                success=False,
                message="Tran ID already exist...",
            )

    # CPS 234: Do not log transaction amounts or card numbers
    logger.info("Transaction added successfully")

    tran_id_display = tran_id.lstrip("0") or "0"
    return AddTransactionResult(
        success=True,
        message=(
            f"Transaction added successfully. "
            f"Your Tran ID is {tran_id_display}."
        ),
        tran_id=tran_id,
    )


# ---------------------------------------------------------------------------
# Bill payment logic
# ---------------------------------------------------------------------------

def validate_bill_payment(
    acct_id: str,
    card_num: str,
    payment_amount: str,
) -> ValidationResult:
    """Validate bill payment input fields.

    Translated from COBIL00C.cbl — 2000-PROCESS-INPUTS.

    Business rules:
    - Account ID must be provided and numeric.
    - Card number must be provided and numeric.
    - Payment amount must be positive and valid decimal.
    - Account must exist in the system.

    Args:
        acct_id: Account ID for the payment.
        card_num: Card number for the payment.
        payment_amount: Payment amount string.

    Returns:
        ValidationResult indicating success or first error.
    """
    if not acct_id.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Account ID must be entered...",
            error_field="acct_id",
        )

    if not acct_id.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Account ID must be Numeric...",
            error_field="acct_id",
        )

    if not card_num.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Card Number must be entered...",
            error_field="card_num",
        )

    if not card_num.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Card Number must be Numeric...",
            error_field="card_num",
        )

    if not payment_amount.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Payment amount must be entered...",
            error_field="payment_amount",
        )

    try:
        amt = Decimal(payment_amount.strip())
        if amt <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="Payment amount must be positive...",
                error_field="payment_amount",
            )
    except InvalidOperation:
        return ValidationResult(
            is_valid=False,
            error_message="Payment amount must be a valid number...",
            error_field="payment_amount",
        )

    return ValidationResult(is_valid=True)


def process_bill_payment(
    acct_id: str,
    card_num: str,
    payment_amount: str,
) -> BillPayResult:
    """Process a bill payment transaction.

    Translated from COBIL00C.cbl — PROCESS-BILL-PAYMENT.

    Business rules:
    - Validates all input fields.
    - Verifies account exists and card belongs to account.
    - Creates a bill payment transaction record.
    - Updates account current balance (debit).

    Args:
        acct_id: Account ID for the payment.
        card_num: Card number for the payment.
        payment_amount: Payment amount string.

    Returns:
        BillPayResult indicating success or failure.
    """
    from python.cards.models import Account, CardXref
    from python.transactions.models import Transaction

    validation = validate_bill_payment(
        acct_id, card_num, payment_amount,
    )
    if not validation.is_valid:
        return BillPayResult(
            success=False,
            message=validation.error_message,
        )

    normalised_acct = acct_id.strip().zfill(11)
    normalised_card = card_num.strip().zfill(16)

    # Verify card belongs to account
    xref = CardXref.objects.filter(
        xref_acct_id=normalised_acct,
        xref_card_num=normalised_card,
    ).first()

    if xref is None:
        return BillPayResult(
            success=False,
            message="Card does not belong to this account...",
        )

    amt = Decimal(payment_amount.strip())
    now = datetime.now().strftime("%Y-%m-%d-%H.%M.%S.%f")

    # Wrap transaction creation + balance update in an atomic block
    # with select_for_update to prevent lost-update race conditions.
    max_retries = 3
    for attempt in range(max_retries):
        tran_id = generate_transaction_id()
        try:
            with transaction.atomic():
                # Lock the account row to prevent concurrent balance updates
                account = (
                    Account.objects
                    .select_for_update()
                    .get(acct_id=normalised_acct)
                )

                Transaction.objects.create(
                    tran_id=tran_id,
                    tran_type_cd=BILL_PAY_TYPE_CD,
                    tran_cat_cd=BILL_PAY_CAT_CD,
                    tran_source=BILL_PAY_SOURCE,
                    tran_desc=f"Bill Payment - Account {normalised_acct}",
                    tran_amt=amt,
                    tran_merchant_id="000000000",
                    tran_merchant_name="BILL PAYMENT",
                    tran_merchant_city="",
                    tran_merchant_zip="",
                    tran_card_num=normalised_card,
                    tran_orig_ts=now,
                    tran_proc_ts=now,
                )

                # Update account balance atomically
                account.acct_curr_bal -= amt
                account.acct_curr_cyc_credit += amt
                account.save()
            break
        except Account.DoesNotExist:
            return BillPayResult(
                success=False,
                message="Account not found...",
            )
        except IntegrityError:
            if attempt == max_retries - 1:
                return BillPayResult(
                    success=False,
                    message="Failed to create payment transaction...",
                )
            continue
        except Exception:
            return BillPayResult(
                success=False,
                message="Failed to create payment transaction...",
            )

    # CPS 234: Do not log account numbers or amounts
    logger.info("Bill payment processed successfully")

    tran_id_display = tran_id.lstrip("0") or "0"
    return BillPayResult(
        success=True,
        message=(
            f"Bill payment processed successfully. "
            f"Confirmation: {tran_id_display}."
        ),
        tran_id=tran_id,
    )


# ---------------------------------------------------------------------------
# Internal helpers (from cotrn02c.py)
# ---------------------------------------------------------------------------

def _is_valid_calendar_date(date_str: str) -> bool:
    """Check that a YYYY-MM-DD string is a real calendar date.

    Mirrors CSUTLDTC in the COBOL program.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _parse_amount(amount_str: str) -> Decimal:
    """Parse a signed amount string into a Decimal.

    Mirrors FUNCTION NUMVAL-C from COBOL.
    Changed from float to Decimal per CPS 234 requirements.
    Input examples: "+00000100.50", "-00000025.00"
    """
    cleaned = amount_str.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0.00")


def _format_amount(amount: Decimal) -> str:
    """Format a Decimal amount to screen format +99999999.99.

    Used when copying last transaction amount to input fields.
    """
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{abs(amount):011.2f}"
