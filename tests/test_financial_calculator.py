import pytest
from services.financial_calculator import FinancialCalculator

def test_emi_calculation():
    # Test standard loan EMI: Principal 500,000, 10.5% p.a., 36 months
    principal = 500000.0
    rate = 10.5
    tenure = 36
    
    emi = FinancialCalculator.calculate_loan_emi(principal, rate, tenure)
    # Expected EMI is around 16,252
    assert 16000 < emi < 16500
    assert isinstance(emi, float)

def test_emi_zero_principal():
    assert FinancialCalculator.calculate_loan_emi(0, 10.5, 36) == 0.0

def test_salary_growth_example_from_spec():
    # Prompt specification:
    # Previous salary: 22,000
    # Current salary: 32,000
    # Monthly salary increase: 10,000
    # Salary increase percentage: 45.45%
    prev_sal = 22000.0
    curr_sal = 32000.0

    result = FinancialCalculator.evaluate_salary_growth(curr_sal, prev_sal)

    assert result["has_previous"] is True
    assert result["difference"] == 10000.0
    assert result["percentage"] == 45.45
    assert result["direction"] == "increase"
    assert "10,000.00" in result["summary"]
    assert "45.45%" in result["summary"]

def test_salary_no_previous():
    result = FinancialCalculator.evaluate_salary_growth(32000.0, None)
    assert result["has_previous"] is False
    assert result["difference"] == 0.0
    assert result["percentage"] == 0.0
