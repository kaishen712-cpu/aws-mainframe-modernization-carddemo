"""
CBSTM03A - Account Statements (Python Translation)

Translated from the COBOL program CBSTM03A.CBL in the AWS CardDemo
mainframe modernization project. This module generates formatted account
statements including customer header, account summary, transaction list,
and running balance. It also produces an HTML version of the statement.

Original: Batch COBOL program that reads cross-reference, transaction,
customer, and account files via the CBSTM03B subroutine, and generates
both plain text and HTML account statements.

The COBOL program uses ALTER/GO TO control flow and 2-dimensional arrays
(WS-CARD-TBL OCCURS 51, WS-TRAN-TBL OCCURS 10). This Python translation
replaces that with structured loops and dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cbstm03b import (
    AccountFileRepository,
    AccountRecord,
    CustomerFileRepository,
    CustomerRecord,
    StatementFileHandler,
    TrnxFileRepository,
    TrnxRecord,
    XrefFileRepository,
    XrefRecord,
    RC_OK,
    RC_EOF,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBSTM03A"
MAX_CARDS_PER_ACCOUNT = 51
MAX_TRANS_PER_CARD = 10


# ---------------------------------------------------------------------------
# Statement data structures
# ---------------------------------------------------------------------------

@dataclass
class StatementTransaction:
    """A single transaction on the statement."""
    tran_id: str = ""
    tran_type_cd: str = ""
    tran_cat_cd: str = ""
    tran_source: str = ""
    tran_desc: str = ""
    tran_amt: float = 0.0
    tran_orig_ts: str = ""
    tran_proc_ts: str = ""


@dataclass
class CardTransactions:
    """Transactions grouped by card number."""
    card_num: str = ""
    transactions: List[StatementTransaction] = field(default_factory=list)


@dataclass
class AccountStatement:
    """Complete account statement data."""
    acct_id: str = ""
    acct_status: str = ""
    acct_curr_bal: float = 0.0
    acct_credit_limit: float = 0.0
    acct_cash_credit_limit: float = 0.0
    acct_open_date: str = ""
    acct_expiration_date: str = ""
    cust_id: str = ""
    cust_first_name: str = ""
    cust_middle_name: str = ""
    cust_last_name: str = ""
    cust_addr_line_1: str = ""
    cust_addr_line_2: str = ""
    cust_addr_line_3: str = ""
    cust_addr_state_cd: str = ""
    cust_addr_zip: str = ""
    card_transactions: List[CardTransactions] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Statement formatting — plain text
# ---------------------------------------------------------------------------

def _format_currency(amount: float) -> str:
    """Format a currency amount as $X,XXX.XX or -$X,XXX.XX."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def format_statement_text(stmt: AccountStatement) -> List[str]:
    """
    Format an account statement as plain text lines.

    Corresponds to the 2000-WRITE-STATEMENTS paragraph in the COBOL
    program. Produces a customer header, account summary, transaction
    list, and running balance.

    Args:
        stmt: The account statement data to format.

    Returns:
        A list of formatted text lines.
    """
    lines: List[str] = []
    sep = "=" * 80

    # Statement header
    lines.append(sep)
    lines.append("ACCOUNT STATEMENT")
    lines.append(sep)
    lines.append("")

    # Customer information
    full_name = " ".join(
        part.strip()
        for part in [
            stmt.cust_first_name,
            stmt.cust_middle_name,
            stmt.cust_last_name,
        ]
        if part.strip()
    )
    lines.append(f"Customer: {full_name}")
    lines.append(f"Customer ID: {stmt.cust_id}")
    if stmt.cust_addr_line_1.strip():
        lines.append(f"Address: {stmt.cust_addr_line_1.strip()}")
    if stmt.cust_addr_line_2.strip():
        lines.append(f"         {stmt.cust_addr_line_2.strip()}")
    if stmt.cust_addr_line_3.strip():
        lines.append(f"         {stmt.cust_addr_line_3.strip()}")
    if stmt.cust_addr_state_cd.strip() or stmt.cust_addr_zip.strip():
        lines.append(f"         {stmt.cust_addr_state_cd.strip()} {stmt.cust_addr_zip.strip()}")
    lines.append("")

    # Account summary
    lines.append(f"Account ID: {stmt.acct_id}")
    lines.append(f"Status: {stmt.acct_status}")
    lines.append(f"Current Balance: {_format_currency(stmt.acct_curr_bal)}")
    lines.append(f"Credit Limit: {_format_currency(stmt.acct_credit_limit)}")
    lines.append(f"Cash Credit Limit: {_format_currency(stmt.acct_cash_credit_limit)}")
    lines.append(f"Open Date: {stmt.acct_open_date}")
    lines.append(f"Expiration Date: {stmt.acct_expiration_date}")
    lines.append("")

    # Transaction details by card
    if stmt.card_transactions:
        lines.append("-" * 80)
        lines.append("TRANSACTIONS")
        lines.append("-" * 80)

        for card_txns in stmt.card_transactions:
            lines.append(f"  Card: {card_txns.card_num}")
            lines.append(
                f"  {'Tran ID':<17}{'Type':>4} {'Cat':>4} "
                f"{'Description':<30}{'Amount':>14}"
            )
            lines.append("  " + "-" * 76)
            for txn in card_txns.transactions:
                lines.append(
                    f"  {txn.tran_id:<17}{txn.tran_type_cd:>4} "
                    f"{txn.tran_cat_cd:>4} "
                    f"{txn.tran_desc[:30]:<30}"
                    f"{_format_currency(txn.tran_amt):>14}"
                )
            lines.append("")

    # Footer
    lines.append(sep)
    lines.append(f"Running Balance: {_format_currency(stmt.acct_curr_bal)}")
    lines.append(sep)

    return lines


# ---------------------------------------------------------------------------
# Statement formatting — HTML
# ---------------------------------------------------------------------------

def format_statement_html(stmt: AccountStatement) -> List[str]:
    """
    Format an account statement as HTML lines.

    Corresponds to the HTML generation sections in the COBOL program
    (3000-WRITE-HTML-STMTS and related paragraphs).

    Args:
        stmt: The account statement data to format.

    Returns:
        A list of HTML lines.
    """
    lines: List[str] = []

    full_name = " ".join(
        part.strip()
        for part in [
            stmt.cust_first_name,
            stmt.cust_middle_name,
            stmt.cust_last_name,
        ]
        if part.strip()
    )

    lines.append("<!DOCTYPE html>")
    lines.append("<html>")
    lines.append("<head>")
    lines.append(f"  <title>Account Statement - {stmt.acct_id}</title>")
    lines.append("  <style>")
    lines.append("    body { font-family: monospace; margin: 20px; }")
    lines.append("    table { border-collapse: collapse; width: 100%; }")
    lines.append("    th, td { border: 1px solid #ddd; padding: 4px 8px; text-align: left; }")
    lines.append("    th { background-color: #f2f2f2; }")
    lines.append("    .amount { text-align: right; }")
    lines.append("    .header { background-color: #333; color: white; padding: 10px; }")
    lines.append("  </style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append('  <div class="header">')
    lines.append("    <h1>Account Statement</h1>")
    lines.append("  </div>")
    lines.append("")

    # Customer info
    lines.append("  <h2>Customer Information</h2>")
    lines.append("  <table>")
    lines.append(f"    <tr><td>Name</td><td>{full_name}</td></tr>")
    lines.append(f"    <tr><td>Customer ID</td><td>{stmt.cust_id}</td></tr>")
    addr_parts = []
    if stmt.cust_addr_line_1.strip():
        addr_parts.append(stmt.cust_addr_line_1.strip())
    if stmt.cust_addr_line_2.strip():
        addr_parts.append(stmt.cust_addr_line_2.strip())
    if stmt.cust_addr_line_3.strip():
        addr_parts.append(stmt.cust_addr_line_3.strip())
    if stmt.cust_addr_state_cd.strip() or stmt.cust_addr_zip.strip():
        addr_parts.append(f"{stmt.cust_addr_state_cd.strip()} {stmt.cust_addr_zip.strip()}")
    lines.append(f"    <tr><td>Address</td><td>{'<br>'.join(addr_parts)}</td></tr>")
    lines.append("  </table>")
    lines.append("")

    # Account summary
    lines.append("  <h2>Account Summary</h2>")
    lines.append("  <table>")
    lines.append(f"    <tr><td>Account ID</td><td>{stmt.acct_id}</td></tr>")
    lines.append(f"    <tr><td>Status</td><td>{stmt.acct_status}</td></tr>")
    lines.append(f"    <tr><td>Current Balance</td><td>{_format_currency(stmt.acct_curr_bal)}</td></tr>")
    lines.append(f"    <tr><td>Credit Limit</td><td>{_format_currency(stmt.acct_credit_limit)}</td></tr>")
    lines.append(f"    <tr><td>Cash Credit Limit</td><td>{_format_currency(stmt.acct_cash_credit_limit)}</td></tr>")
    lines.append(f"    <tr><td>Open Date</td><td>{stmt.acct_open_date}</td></tr>")
    lines.append(f"    <tr><td>Expiration Date</td><td>{stmt.acct_expiration_date}</td></tr>")
    lines.append("  </table>")
    lines.append("")

    # Transactions
    if stmt.card_transactions:
        lines.append("  <h2>Transactions</h2>")
        for card_txns in stmt.card_transactions:
            lines.append(f"  <h3>Card: {card_txns.card_num}</h3>")
            lines.append("  <table>")
            lines.append("    <tr>")
            lines.append("      <th>Tran ID</th>")
            lines.append("      <th>Type</th>")
            lines.append("      <th>Category</th>")
            lines.append("      <th>Description</th>")
            lines.append('      <th class="amount">Amount</th>')
            lines.append("    </tr>")
            for txn in card_txns.transactions:
                lines.append("    <tr>")
                lines.append(f"      <td>{txn.tran_id}</td>")
                lines.append(f"      <td>{txn.tran_type_cd}</td>")
                lines.append(f"      <td>{txn.tran_cat_cd}</td>")
                lines.append(f"      <td>{txn.tran_desc.strip()}</td>")
                lines.append(f'      <td class="amount">{_format_currency(txn.tran_amt)}</td>')
                lines.append("    </tr>")
            lines.append("  </table>")
        lines.append("")

    lines.append(f"  <p><strong>Running Balance: {_format_currency(stmt.acct_curr_bal)}</strong></p>")
    lines.append("</body>")
    lines.append("</html>")

    return lines


# ---------------------------------------------------------------------------
# Main statement generation
# ---------------------------------------------------------------------------

def _collect_transactions_for_account(
    handler: StatementFileHandler,
    xref: XrefRecord,
    all_xrefs_for_account: List[XrefRecord],
) -> List[CardTransactions]:
    """
    Collect all transactions for an account across its cards.

    Corresponds to the 2-dimensional array population in the COBOL
    program (WS-TRNX-TABLE with WS-CARD-TBL and WS-TRAN-TBL).
    Instead of fixed-size arrays, we use lists.
    """
    card_txns_map: Dict[str, List[StatementTransaction]] = {}
    card_nums = [x.xref_card_num for x in all_xrefs_for_account]

    for card_num in card_nums:
        card_txns_map[card_num] = []

    # Read all transactions and assign to cards
    while True:
        result = handler.read_next_trnx()
        if result.return_code == RC_EOF:
            break
        if result.return_code != RC_OK:
            break
        trnx: TrnxRecord = result.data  # type: ignore[assignment]
        if trnx.trnx_card_num in card_txns_map:
            stmt_txn = StatementTransaction(
                tran_id=trnx.trnx_id,
                tran_type_cd=trnx.trnx_type_cd,
                tran_cat_cd=trnx.trnx_cat_cd,
                tran_source=trnx.trnx_source,
                tran_desc=trnx.trnx_desc,
                tran_amt=trnx.trnx_amt,
                tran_orig_ts=trnx.trnx_orig_ts,
                tran_proc_ts=trnx.trnx_proc_ts,
            )
            card_txns_map[trnx.trnx_card_num].append(stmt_txn)

    result_list: List[CardTransactions] = []
    for card_num in card_nums:
        txns = card_txns_map[card_num]
        if txns:
            result_list.append(CardTransactions(card_num=card_num, transactions=txns))

    return result_list


def generate_account_statements(
    trnx_repo: TrnxFileRepository,
    xref_repo: XrefFileRepository,
    cust_repo: CustomerFileRepository,
    acct_repo: AccountFileRepository,
) -> List[AccountStatement]:
    """
    Generate account statements for all accounts.

    This is the main entry point corresponding to the COBOL program's
    PROCEDURE DIVISION. It:
    1. Opens all files via the StatementFileHandler (CBSTM03B)
    2. Reads cross-reference records sequentially to find accounts
    3. For each unique account, reads customer and account data
    4. Collects transactions grouped by card
    5. Builds an AccountStatement for each account

    Args:
        trnx_repo: Repository for sequential transaction file access.
        xref_repo: Repository for sequential cross-reference file access.
        cust_repo: Repository for keyed customer file access.
        acct_repo: Repository for keyed account file access.

    Returns:
        A list of AccountStatement objects, one per account.
    """
    handler = StatementFileHandler(trnx_repo, xref_repo, cust_repo, acct_repo)
    handler.open_all()

    # Collect all xref records grouped by account
    account_xrefs: Dict[str, List[XrefRecord]] = {}
    xref_order: List[str] = []

    while True:
        result = handler.read_next_xref()
        if result.return_code == RC_EOF:
            break
        if result.return_code != RC_OK:
            break
        xref: XrefRecord = result.data  # type: ignore[assignment]
        acct_id = xref.xref_acct_id
        if acct_id not in account_xrefs:
            account_xrefs[acct_id] = []
            xref_order.append(acct_id)
        account_xrefs[acct_id].append(xref)

    statements: List[AccountStatement] = []

    for acct_id in xref_order:
        xrefs = account_xrefs[acct_id]
        first_xref = xrefs[0]

        # Read customer record
        cust_result = handler.read_customer_by_key(first_xref.xref_cust_id)
        cust: Optional[CustomerRecord] = None
        if cust_result.return_code == RC_OK:
            cust = cust_result.data  # type: ignore[assignment]

        # Read account record
        acct_result = handler.read_account_by_key(acct_id)
        acct: Optional[AccountRecord] = None
        if acct_result.return_code == RC_OK:
            acct = acct_result.data  # type: ignore[assignment]

        # Collect transactions
        card_txns = _collect_transactions_for_account(handler, first_xref, xrefs)

        # Build statement
        stmt = AccountStatement(
            acct_id=acct_id,
            acct_status=acct.acct_active_status if acct else "",
            acct_curr_bal=acct.acct_curr_bal if acct else 0.0,
            acct_credit_limit=acct.acct_credit_limit if acct else 0.0,
            acct_cash_credit_limit=acct.acct_cash_credit_limit if acct else 0.0,
            acct_open_date=acct.acct_open_date if acct else "",
            acct_expiration_date=acct.acct_expiration_date if acct else "",
            cust_id=first_xref.xref_cust_id,
            cust_first_name=cust.cust_first_name if cust else "",
            cust_middle_name=cust.cust_middle_name if cust else "",
            cust_last_name=cust.cust_last_name if cust else "",
            cust_addr_line_1=cust.cust_addr_line_1 if cust else "",
            cust_addr_line_2=cust.cust_addr_line_2 if cust else "",
            cust_addr_line_3=cust.cust_addr_line_3 if cust else "",
            cust_addr_state_cd=cust.cust_addr_state_cd if cust else "",
            cust_addr_zip=cust.cust_addr_zip if cust else "",
            card_transactions=card_txns,
        )
        statements.append(stmt)

    handler.close_all()
    return statements


def generate_statement_report(
    trnx_repo: TrnxFileRepository,
    xref_repo: XrefFileRepository,
    cust_repo: CustomerFileRepository,
    acct_repo: AccountFileRepository,
) -> List[str]:
    """
    Generate all account statements as formatted text lines.

    Convenience function that generates statements and formats them
    as plain text.

    Args:
        trnx_repo: Repository for sequential transaction file access.
        xref_repo: Repository for sequential cross-reference file access.
        cust_repo: Repository for keyed customer file access.
        acct_repo: Repository for keyed account file access.

    Returns:
        A list of formatted text lines for all statements.
    """
    statements = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
    lines: List[str] = []
    for stmt in statements:
        lines.extend(format_statement_text(stmt))
        lines.append("")  # blank line between statements
    return lines


def generate_statement_html(
    trnx_repo: TrnxFileRepository,
    xref_repo: XrefFileRepository,
    cust_repo: CustomerFileRepository,
    acct_repo: AccountFileRepository,
) -> List[str]:
    """
    Generate all account statements as HTML lines.

    Convenience function that generates statements and formats them
    as HTML.

    Args:
        trnx_repo: Repository for sequential transaction file access.
        xref_repo: Repository for sequential cross-reference file access.
        cust_repo: Repository for keyed customer file access.
        acct_repo: Repository for keyed account file access.

    Returns:
        A list of HTML lines for all statements.
    """
    statements = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
    lines: List[str] = []
    for stmt in statements:
        lines.extend(format_statement_html(stmt))
        lines.append("")
    return lines
