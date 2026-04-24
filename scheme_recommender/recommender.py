import json
import re
import os

def parse_land_limit(limit_str):
    match = re.search(r'([\d.]+)', limit_str)
    if match:
        return float(match.group(1))
    return float('inf')

def parse_income_limit(limit_str):
    # Removing commas to easily parse numbers like 15,000
    limit_str = limit_str.replace(',', '')
    match = re.search(r'([\d]+)', limit_str)
    if match:
        return float(match.group(1))
    return float('inf')

import os

def load_schemes():
    schemes = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(base_dir, 'central_govt_schemes.json'), 'r', encoding='utf-8') as f:
        central = json.load(f)
        for s in central:
            s['source'] = 'Central Government'
        schemes.extend(central)
        
    with open(os.path.join(base_dir, 'kerala_govt_schemes.json'), 'r', encoding='utf-8') as f:
        kerala = json.load(f)
        for s in kerala:
            s['source'] = 'Kerala Government'
        schemes.extend(kerala)
        
    return schemes

def recommend_schemes(monthly_income, land_size_hectares, crop_type):
    schemes = load_schemes()
    recommended = []
    
    # Normalize crop_type input for comparison
    crop_type_lower = crop_type.lower().strip()
    
    for scheme in schemes:
        land_limit = parse_land_limit(scheme.get('Land limit', ''))
        income_limit = parse_income_limit(scheme.get('income_limit', ''))
        eligible_crops = [c.lower() for c in scheme.get('eligible_crops', ['all'])]
        
        # Typically, a farmer is eligible if their land and income are <= the limits
        if land_size_hectares <= land_limit and monthly_income <= income_limit:
            if "all" in eligible_crops or crop_type_lower in eligible_crops:
                recommended.append(scheme)
            
    return recommended

def main():
    print("Welcome to the Farmer Scheme Recommendation Agent")
    print("-" * 50)
    
    try:
        monthly_income = float(input("Enter your monthly income (in ₹): "))
        land_size = float(input("Enter your land size (in hectares): "))
        crop_type = input("Enter your primary crop type (e.g., rubber, paddy, coconut, pepper): ")
    except ValueError:
        print("Invalid input. Please enter numeric values for income and land.")
        return

    suitable_schemes = recommend_schemes(monthly_income, land_size, crop_type)
    
    print("\n" + "="*50)
    print(f"Found {len(suitable_schemes)} suitable scheme(s) for you:")
    print("="*50)
    
    for idx, scheme in enumerate(suitable_schemes, 1):
        print(f"\n{idx}. {scheme['scheme_name']} ({scheme['source']})")
        print(f"   Type: {scheme['type']}")
        print(f"   Benefit: {scheme.get('benifit', 'N/A')}")
        eligible_crops_str = ", ".join(scheme.get('eligible_crops', ['all'])).title()
        print(f"   Eligibility Criteria: Land up to {scheme.get('Land limit')}, Income up to {scheme.get('income_limit')}, Crops: {eligible_crops_str}")

if __name__ == "__main__":
    main()
