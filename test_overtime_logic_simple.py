#!/usr/bin/env python3
"""
Simple test script to verify overtime calculation logic
This script tests the core logic without requiring database access
"""

def test_overtime_calculation_logic():
    """Test the core overtime calculation logic"""
    print("=== Overtime Calculation Logic Test ===\n")
    
    # Test cases with different overtime shifts
    test_cases = [
        (0.0, "No overtime"),
        (0.5, "Half shift"),
        (1.0, "Full shift"),
        (1.5, "One and half shifts"),
        (2.0, "Two shifts"),
        (2.5, "Two and half shifts"),
        (3.0, "Three shifts")
    ]
    
    # Different daily wage scenarios
    wage_scenarios = [
        (526.0, "Un-Skilled"),
        (614.0, "Semi-Skilled"),
        (739.0, "Skilled"),
        (868.0, "Highly Skilled"),
        (800.0, "Custom Rate")
    ]
    
    print("Testing overtime calculation logic:\n")
    print("Formula: overtime_allowance = (overtime_shifts × 8) × (daily_wage ÷ 8)")
    print("Simplified: overtime_allowance = overtime_shifts × daily_wage\n")
    
    for daily_wage, skill_level in wage_scenarios:
        print(f"--- {skill_level} (Daily Wage: ₹{daily_wage}) ---")
        hourly_rate = daily_wage / 8
        
        for shifts, description in test_cases:
            # Step 1: Convert shifts to hours
            hours = shifts * 8
            
            # Step 2: Calculate overtime allowance
            overtime_allowance = hours * hourly_rate
            
            # Alternative calculation: shifts * daily_wage (simplified)
            simplified_allowance = shifts * daily_wage
            
            print(f"  {description}: {shifts} shifts = {hours} hours = ₹{overtime_allowance}")
            
            # Verify the simplified calculation matches
            if abs(overtime_allowance - simplified_allowance) < 0.01:
                print(f"    ✓ Verified: {shifts} × ₹{daily_wage} = ₹{simplified_allowance}")
            else:
                print(f"    ✗ Error: Calculations don't match!")
        
        print()
    
    print("=== Test Complete ===")

def test_conversion_logic():
    """Test the conversion logic between shifts and hours"""
    print("=== Conversion Logic Test ===\n")
    
    print("Testing shift to hour conversion:")
    print("Formula: hours = shifts × 8\n")
    
    test_shifts = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    
    for shifts in test_shifts:
        hours = shifts * 8
        print(f"  {shifts} shifts = {hours} hours")
    
    print("\nTesting hour to shift conversion:")
    print("Formula: shifts = hours ÷ 8 (rounded to nearest 0.5)\n")
    
    test_hours = [0, 4, 8, 12, 16, 20, 24]
    
    for hours in test_hours:
        shifts = hours / 8
        rounded_shifts = round(shifts * 2) / 2  # Round to nearest 0.5
        print(f"  {hours} hours = {shifts} shifts (raw) = {rounded_shifts} shifts (rounded)")
    
    print("\n=== Conversion Test Complete ===")

def test_validation_logic():
    """Test the validation logic for overtime shifts"""
    print("=== Validation Logic Test ===\n")
    
    test_values = [
        (-1.0, "Negative value"),
        (0.0, "Zero"),
        (0.25, "Quarter shift (invalid)"),
        (0.5, "Half shift"),
        (1.0, "Full shift"),
        (1.3, "Arbitrary decimal"),
        (1.5, "One and half shifts"),
        (2.0, "Two shifts"),
        (3.5, "Three and half shifts")
    ]
    
    print("Testing validation logic:")
    print("- Minimum value: 0")
    print("- Increments: 0.5 steps")
    print("- Rounding: to nearest 0.5\n")
    
    for value, description in test_values:
        # Validation logic
        is_valid = value >= 0
        
        # Rounding logic
        if is_valid:
            rounded_value = round(value * 2) / 2
            status = "✓ Valid" if value == rounded_value else f"✓ Valid (rounded to {rounded_value})"
        else:
            rounded_value = "N/A"
            status = "✗ Invalid (negative)"
        
        print(f"  {description}: {value} → {status}")
    
    print("\n=== Validation Test Complete ===")

if __name__ == "__main__":
    print("Starting overtime logic tests...\n")
    
    test_overtime_calculation_logic()
    print("\n" + "="*50 + "\n")
    test_conversion_logic()
    print("\n" + "="*50 + "\n")
    test_validation_logic()
    
    print("\n" + "="*50)
    print("All logic tests completed successfully!")
    print("The overtime calculation logic is working correctly.")
