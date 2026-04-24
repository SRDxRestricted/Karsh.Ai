import json
import re

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

def load_schemes():
    schemes = []
    with open('central_govt_schemes.json', 'r', encoding='utf-8') as f:
        central = json.load(f)
        for s in central:
            s['source'] = 'Central Government'
        schemes.extend(central)
        
    with open('kerala_govt_schemes.json', 'r', encoding='utf-8') as f:
        kerala = json.load(f)
        for s in kerala:
            s['source'] = 'Kerala Government'
        schemes.extend(kerala)
        
    return schemes

def recommend_schemes(monthly_income, land_size_hectares):
    schemes = load_schemes()
    recommended = []
    
    for scheme in schemes:
        land_limit = parse_land_limit(scheme.get('Land limit', ''))
        income_limit = parse_income_limit(scheme.get('income_limit', ''))
        
        # Typically, a farmer is eligible if their land and income are <= the limits
        if land_size_hectares <= land_limit and monthly_income <= income_limit:
            recommended.append(scheme)
            
    return recommended

def main():
    print("Welcome to the Farmer Scheme Recommendation Agent")
    print("-" * 50)
    
    try:
        monthly_income = float(input("Enter your monthly income (in ₹): "))
        land_size = float(input("Enter your land size (in hectares): "))
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        return

    suitable_schemes = recommend_schemes(monthly_income, land_size)
    
    print("\n" + "="*50)
    print(f"Found {len(suitable_schemes)} suitable scheme(s) for you:")
    print("="*50)
    
    for idx, scheme in enumerate(suitable_schemes, 1):
        print(f"\n{idx}. {scheme['scheme_name']} ({scheme['source']})")
        print(f"   Type: {scheme['type']}")
        print(f"   Benefit: {scheme.get('benifit', 'N/A')}")
        print(f"   Eligibility Criteria: Land up to {scheme.get('Land limit')}, Income up to {scheme.get('income_limit')}")

if __name__ == "__main__":
    main()
