"""
List of non-company securities to exclude from the game.
These are bonds, notes, preferred stocks, warrants, rights, units, and other special securities
that are not actual operating companies.
"""

# High confidence exclusions - these definitely should not be in the game
HIGH_CONFIDENCE_EXCLUSIONS = {
    'AACBR', 'AACBU', 'ABVEW', 'BC-PA', 'BFRGW', 'BTSGU', 'BULLW', 'CELV',
    'CMRC', 'COLA', 'COLAR', 'CORZZ', 'DAAQU', 'DAICW', 'DHAIW', 'DMAAR',
    'DMAAU', 'DSYWW', 'EBRGF', 'ENGNW', 'ENJ', 'ENO', 'FBYDW', 'FERAR',
    'FGMCR', 'GCLWW', 'GENVR', 'GL-PD', 'GTENU', 'GTENW', 'IPCXU', 'IPODU',
    'KIDZW', 'LCCCR', 'LOKVU', 'LOKVW', 'LOTWW', 'MBAVU', 'MNYWW', 'MRNOW',
    'NAMMW', 'NEE-PN', 'NMPAU', 'NPACU', 'NPACW', 'NVNIW', 'OAK-PA', 'PACHU',
    'PCG-PC', 'PCG-PI', 'PDM', 'PFBC', 'QSEAU', 'RIBBR', 'RZLVW', 'SCAGW',
    'SHMDW', 'SOJD', 'SOJE', 'STRD', 'STRF', 'TACHU', 'TDACW', 'TVACU',
    'USB-PA', 'USB-PS', 'UYSCU', 'VAL-WT', 'VAPEW', 'WRB-PE', 'WRB-PF',
    'WRB-PG', 'WRB-PH', 'WTGUR'
}

# Patterns that indicate non-company securities
EXCLUSION_PATTERNS = {
    'ticker_suffixes': [
        '-PA', '-PB', '-PC', '-PD', '-PE', '-PF', '-PG', '-PH', '-PI', '-PJ',
        '-PK', '-PL', '-PM', '-PN', '-PO', '-PP', '-PQ', '-PR', '-PS', '-PT',
        '-PU', '-PV', '-PW', '-PX', '-PY', '-PZ',  # Preferred stocks
        '-WT', '.WT',  # Warrants
        '-UN', '.UN',  # Units
        '-A', '-B', '-C', '-D',  # Class shares (some are valid, some not)
    ],
    'name_keywords': [
        'Series', 'Preferred', 'Notes', 'Bonds', 'Warrants', 'Rights', 'Units',
        'Trust', 'Debentures', 'Depositary', 'Cumulative', 'Convertible',
        'Redeemable', 'Perpetual', 'Floating', 'Fixed Rate'
    ],
    'name_patterns': [
        r'\d+\.?\d*%',  # Interest rates (5%, 5.25%)
        r'Due \d{4}',   # Maturity dates
    ]
}


def is_excluded_security(ticker: str, name: str = None) -> bool:
    """
    Check if a security should be excluded from the game.
    
    Args:
        ticker: The stock ticker
        name: The company name (optional, but recommended for better accuracy)
    
    Returns:
        True if the security should be excluded, False otherwise
    """
    # Check high confidence exclusions first
    if ticker in HIGH_CONFIDENCE_EXCLUSIONS:
        return True
    
    # Check ticker patterns
    ticker_upper = ticker.upper()
    for suffix in EXCLUSION_PATTERNS['ticker_suffixes']:
        if ticker_upper.endswith(suffix):
            return True
    
    # Check name patterns if provided
    if name:
        name_upper = name.upper()
        
        # Check for keywords
        for keyword in EXCLUSION_PATTERNS['name_keywords']:
            if keyword.upper() in name_upper:
                return True
        
        # Check for patterns (like interest rates)
        import re
        for pattern in EXCLUSION_PATTERNS['name_patterns']:
            if re.search(pattern, name, re.IGNORECASE):
                return True
    
    return False


def get_excluded_tickers_from_list(tickers: list) -> list:
    """
    Filter a list of tickers to get only those that should be excluded.
    
    Args:
        tickers: List of ticker symbols
    
    Returns:
        List of tickers that should be excluded
    """
    return [ticker for ticker in tickers if is_excluded_security(ticker)]


def get_valid_tickers_from_list(tickers: list) -> list:
    """
    Filter a list of tickers to get only valid operating companies.
    
    Args:
        tickers: List of ticker symbols
    
    Returns:
        List of tickers that are valid operating companies
    """
    return [ticker for ticker in tickers if not is_excluded_security(ticker)]


# Example usage
if __name__ == "__main__":
    # Test with some examples
    test_cases = [
        ('AAPL', 'Apple Inc.'),  # Should pass
        ('BC-PA', 'Brunswick Corporation 6.500% Se'),  # Should be excluded
        ('MSFT', 'Microsoft Corporation'),  # Should pass
        ('VAL-WT', 'Valaris Limited Warrants'),  # Should be excluded
        ('GOOGL', 'Alphabet Inc.'),  # Should pass
    ]
    
    print("Security Exclusion Test Results:")
    print("-" * 60)
    for ticker, name in test_cases:
        excluded = is_excluded_security(ticker, name)
        status = "EXCLUDED" if excluded else "VALID"
        print(f"{ticker:10} {name:40} -> {status}")