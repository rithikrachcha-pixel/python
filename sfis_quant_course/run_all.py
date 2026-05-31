"""
SFIS Quant Course — Master Runner
Run all modules sequentially or pick individual ones.
"""

import subprocess
import sys
from pathlib import Path

MODULES = [
    ("Module 1A: Probability & Statistics",    "module_01_foundations/01_probability_statistics.py"),
    ("Module 1B: Linear Algebra & Calculus",   "module_01_foundations/02_linear_algebra_calculus.py"),
    ("Module 2:  Time Value & Fixed Income",   "module_02_financial_math/01_time_value_fixed_income.py"),
    ("Module 3:  Data Analysis & Engineering", "module_03_data_analysis/01_market_data_engineering.py"),
    ("Module 4:  Portfolio Theory (MPT)",      "module_04_portfolio_theory/01_modern_portfolio_theory.py"),
    ("Module 5:  Options Pricing",             "module_05_derivatives/01_options_pricing.py"),
    ("Module 6A: Momentum Strategies",         "module_06_strategies/01_momentum_strategy.py"),
    ("Module 6B: Pairs Trading / Stat Arb",    "module_06_strategies/02_mean_reversion_pairs.py"),
    ("Module 7:  Risk Management",             "module_07_risk_management/01_var_cvar_stress.py"),
    ("Module 8:  ML Alpha Generation",         "module_08_machine_learning/01_ml_alpha_generation.py"),
    ("Module 9:  Backtesting Framework",       "module_09_backtesting/01_backtesting_framework.py"),
    ("Module 10: Execution & Microstructure",  "module_10_execution/01_market_microstructure.py"),
    ("CAPSTONE:  Full Fund Simulation",        "capstone/sfis_quant_fund.py"),
]


def run_module(path: str) -> bool:
    result = subprocess.run([sys.executable, path], capture_output=False)
    return result.returncode == 0


def print_menu():
    print("\n" + "="*65)
    print("  SFIS Quant Finance Course — Southampton Finance & Investment Society")
    print("="*65)
    print()
    for i, (name, _) in enumerate(MODULES, 1):
        print(f"  {i:2d}. {name}")
    print(f"\n   A. Run ALL modules")
    print(f"   Q. Quit")
    print()


if __name__ == "__main__":
    # If a module number is passed as arg, run just that one
    if len(sys.argv) > 1:
        idx = int(sys.argv[1]) - 1
        if 0 <= idx < len(MODULES):
            name, path = MODULES[idx]
            print(f"\nRunning: {name}")
            run_module(path)
        sys.exit(0)

    while True:
        print_menu()
        choice = input("Select module (1-13, A, Q): ").strip().upper()

        if choice == "Q":
            print("Goodbye!")
            break
        elif choice == "A":
            for name, path in MODULES:
                print(f"\n{'='*65}")
                print(f"  Running: {name}")
                print("="*65)
                success = run_module(path)
                if not success:
                    print(f"  [!] Module failed: {path}")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(MODULES):
                name, path = MODULES[idx]
                print(f"\nRunning: {name}")
                run_module(path)
            else:
                print("Invalid choice.")
        else:
            print("Invalid choice.")
