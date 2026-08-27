"""
ISO 10962 CFI (Classification of Financial Instruments) Code Decoder.
Decodes 6-letter CFI codes (e.g. ESVUFR, DBFTFR, OCSXPS) into human-readable descriptions.
"""

from typing import Dict, Any, Tuple


CATEGORIES = {
    'E': 'Equities',
    'D': 'Debt Instruments',
    'R': 'Entitlements (Rights)',
    'O': 'Options',
    'F': 'Futures',
    'M': 'Miscellaneous / Others',
    'C': 'Collective Investment Vehicles',
    'S': 'Spot',
    'J': 'Forwards',
    'K': 'Strategies',
    'L': 'Financing',
    'T': 'Referential Instruments',
}

EQUITY_GROUPS = {
    'S': 'Common / Ordinary Shares',
    'P': 'Preferred / Preference Shares',
    'R': 'Convertible Preference Shares',
    'U': 'Units (e.g. REITs, Trust Units)',
    'C': 'Other Equity Interests',
    'F': 'Structured Instruments (Equity)',
}

DEBT_GROUPS = {
    'B': 'Bonds',
    'C': 'Convertible Bonds',
    'W': 'Bonds with Warrants',
    'M': 'Medium Term Notes',
    'M': 'Money Market Instruments',
    'T': 'Treasury Bills',
    'Y': 'Money Market Instruments',
    'S': 'Structured Instruments (Debt)',
    'E': 'Mortgage-Backed Securities',
    'A': 'Asset-Backed Securities',
}

OPTION_GROUPS = {
    'C': 'Call Option',
    'P': 'Put Option',
    'M': 'Other / Mixed Option',
}

FUTURE_GROUPS = {
    'F': 'Financial Future',
    'C': 'Commodity Future',
}


def decode_cfi(cfi: str) -> Dict[str, Any]:
    """
    Decodes an ISO 10962 CFI code into structural components and human summary.
    """
    if not cfi or len(cfi) != 6:
        return {
            "code": cfi or "UNKNOWN",
            "is_valid": False,
            "category": "Invalid/Unknown",
            "group": "Unknown",
            "summary": f"Invalid CFI format ('{cfi}')",
        }

    cfi = cfi.upper()
    cat_code = cfi[0]
    grp_code = cfi[1]
    attr1, attr2, attr3, attr4 = cfi[2], cfi[3], cfi[4], cfi[5]

    cat_name = CATEGORIES.get(cat_code, f"Unknown Category ({cat_code})")
    group_name = "Standard"

    details = []

    if cat_code == 'E':  # Equities
        group_name = EQUITY_GROUPS.get(grp_code, f"Equity Group ({grp_code})")
        # Voting rights (Attr 1)
        voting = {'V': 'Voting', 'N': 'Non-Voting', 'R': 'Restricted Voting', 'X': 'Not Applicable'}.get(attr1, attr1)
        # Ownership / Transferability (Attr 2)
        ownership = {'T': 'Restrictions', 'U': 'Free/Unrestricted', 'X': 'Not Applicable'}.get(attr2, attr2)
        # Payment status (Attr 3)
        payment = {'F': 'Fully Paid', 'P': 'Partially Paid', 'N': 'Nil Paid', 'X': 'Not Applicable'}.get(attr3, attr3)
        # Form (Attr 4)
        form = {'B': 'Bearer', 'R': 'Registered', 'N': 'Bearer & Registered', 'X': 'Not Applicable'}.get(attr4, attr4)

        details = [f"Voting: {voting}", f"Transfer: {ownership}", f"Payment: {payment}", f"Form: {form}"]

    elif cat_code == 'D':  # Debt
        group_name = DEBT_GROUPS.get(grp_code, f"Debt Group ({grp_code})")
        # Interest type (Attr 1)
        interest = {'F': 'Fixed rate', 'V': 'Variable/Floating rate', 'Z': 'Zero coupon', 'X': 'Other'}.get(attr1, attr1)
        # Guarantee (Attr 2)
        guarantee = {'T': 'Government/Treasury', 'G': 'Guaranteed', 'U': 'Unsecured', 'S': 'Secured', 'X': 'Other'}.get(attr2, attr2)
        # Redemption (Attr 3)
        redemption = {'F': 'Fixed maturity', 'C': 'Callable', 'P': 'Putable', 'T': 'Extendible', 'X': 'Other'}.get(attr3, attr3)
        # Form (Attr 4)
        form = {'B': 'Bearer', 'R': 'Registered', 'X': 'Other'}.get(attr4, attr4)

        details = [f"Interest: {interest}", f"Guarantee: {guarantee}", f"Redemption: {redemption}", f"Form: {form}"]

    elif cat_code in ('O', 'F'):  # Options or Futures
        if cat_code == 'O':
            group_name = OPTION_GROUPS.get(grp_code, f"Option Group ({grp_code})")
            exercise = {'A': 'American', 'E': 'European', 'B': 'Bermudan', 'X': 'Other'}.get(attr1, attr1)
            underlying = {'S': 'Equities', 'D': 'Debt', 'C': 'Currencies', 'I': 'Indices', 'T': 'Commodities', 'X': 'Other'}.get(attr2, attr2)
            delivery = {'P': 'Physical', 'C': 'Cash', 'X': 'Other'}.get(attr3, attr3)
            standard = {'S': 'Standardized', 'N': 'Non-standardized', 'X': 'Other'}.get(attr4, attr4)
            details = [f"Exercise: {exercise}", f"Underlying: {underlying}", f"Delivery: {delivery}", f"Type: {standard}"]
        else:
            group_name = FUTURE_GROUPS.get(grp_code, f"Future Group ({grp_code})")
            underlying = {'S': 'Equities', 'D': 'Debt', 'C': 'Currencies', 'I': 'Indices', 'T': 'Commodities', 'X': 'Other'}.get(attr1, attr1)
            delivery = {'P': 'Physical', 'C': 'Cash', 'X': 'Other'}.get(attr2, attr2)
            standard = {'S': 'Standardized', 'N': 'Non-standardized', 'X': 'Other'}.get(attr3, attr3)
            details = [f"Underlying: {underlying}", f"Delivery: {delivery}", f"Type: {standard}"]

    summary = f"{cat_name} -> {group_name}"
    if details:
        summary += f" ({', '.join(details)})"

    return {
        "code": cfi,
        "is_valid": True,
        "category": cat_name,
        "group": group_name,
        "details": details,
        "summary": summary,
    }
