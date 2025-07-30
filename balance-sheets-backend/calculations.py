"""Financial ratio calculations"""
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FinancialCalculator:
    """Calculate financial ratios and metrics"""
    
    @staticmethod
    def safe_divide(numerator: Decimal, denominator: Decimal) -> Optional[Decimal]:
        """Safely divide two decimals, returning None if denominator is zero"""
        if denominator == 0:
            return None
        return numerator / denominator
    
    @staticmethod
    def calculate_pe_ratio(stock_price: Decimal, net_income: Decimal, shares_outstanding: Decimal) -> Optional[Decimal]:
        """Calculate Price-to-Earnings ratio
        
        P/E = Stock Price / Earnings Per Share
        EPS = Net Income / Shares Outstanding
        """
        if shares_outstanding == 0 or net_income <= 0:
            return None
        
        eps = net_income / shares_outstanding
        return FinancialCalculator.safe_divide(stock_price, eps)
    
    @staticmethod
    def calculate_pb_ratio(market_cap: Decimal, equity: Decimal) -> Optional[Decimal]:
        """Calculate Price-to-Book ratio
        
        P/B = Market Cap / Book Value (Total Equity)
        """
        return FinancialCalculator.safe_divide(market_cap, equity)
    
    @staticmethod
    def calculate_debt_to_equity(debt: Decimal, equity: Decimal) -> Optional[Decimal]:
        """Calculate Debt-to-Equity ratio
        
        D/E = Total Debt / Total Equity
        """
        return FinancialCalculator.safe_divide(debt, equity)
    
    @staticmethod
    def calculate_current_ratio(assets: Decimal, liabilities: Decimal) -> Optional[Decimal]:
        """Calculate Current ratio (simplified using total assets/liabilities)
        
        Note: This is a simplified version. Ideally we'd use current assets/current liabilities
        """
        return FinancialCalculator.safe_divide(assets, liabilities)
    
    @staticmethod
    def calculate_roe(net_income: Decimal, equity: Decimal) -> Optional[Decimal]:
        """Calculate Return on Equity
        
        ROE = Net Income / Total Equity
        """
        return FinancialCalculator.safe_divide(net_income, equity)
    
    @staticmethod
    def calculate_difficulty_score(
        pe_ratio: Optional[Decimal],
        pb_ratio: Optional[Decimal],
        debt_to_equity: Optional[Decimal],
        market_cap: Decimal
    ) -> int:
        """Calculate a difficulty score from 1-10 based on various factors
        
        Higher scores = more difficult to evaluate
        Factors considered:
        - Missing ratios increase difficulty
        - Extreme ratios increase difficulty
        - Smaller companies are generally harder to evaluate
        """
        score = 5  # Base score
        
        # Missing data increases difficulty
        if pe_ratio is None:
            score += 1
        elif pe_ratio < 0 or pe_ratio > 100:
            score += 2  # Extreme P/E ratios
        
        if pb_ratio is None:
            score += 1
        elif pb_ratio > 10:
            score += 1  # High P/B ratio
        
        if debt_to_equity is None:
            score += 1
        elif debt_to_equity > 3:
            score += 1  # High leverage
        
        # Market cap factor (smaller = harder)
        if market_cap < 1_000_000_000:  # Under $1B
            score += 2
        elif market_cap < 10_000_000_000:  # Under $10B
            score += 1
        
        # Ensure score is within bounds
        return max(1, min(10, score))
    
    @staticmethod
    def calculate_all_metrics(
        stock_price: Decimal,
        market_cap: Decimal,
        net_income: Decimal,
        shares_outstanding: Decimal,
        assets: Decimal,
        liabilities: Decimal,
        equity: Decimal,
        debt: Decimal
    ) -> dict:
        """Calculate all financial metrics
        
        Returns a dictionary with all calculated ratios
        """
        pe_ratio = FinancialCalculator.calculate_pe_ratio(stock_price, net_income, shares_outstanding)
        pb_ratio = FinancialCalculator.calculate_pb_ratio(market_cap, equity)
        debt_to_equity = FinancialCalculator.calculate_debt_to_equity(debt, equity)
        current_ratio = FinancialCalculator.calculate_current_ratio(assets, liabilities)
        roe = FinancialCalculator.calculate_roe(net_income, equity)
        
        difficulty_score = FinancialCalculator.calculate_difficulty_score(
            pe_ratio, pb_ratio, debt_to_equity, market_cap
        )
        
        return {
            'p_e_ratio': round(pe_ratio, 2) if pe_ratio else None,
            'p_b_ratio': round(pb_ratio, 2) if pb_ratio else None,
            'debt_to_equity': round(debt_to_equity, 2) if debt_to_equity else None,
            'current_ratio': round(current_ratio, 2) if current_ratio else None,
            'roe': round(roe * 100, 2) if roe else None,  # Convert to percentage
            'difficulty_score': difficulty_score
        }