import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder

# Global variables to store our trained model and encoders
clf = None
encoders = {}
average_prices = {}

# Average yield per hectare in standard units (kg or nuts)
YIELD_PER_HA = {
    "Coconut": 10000,       # nuts
    "Banana": 25000,        # kg
    "Rubber": 1500,         # kg
    "Black Pepper": 500,    # kg
    "Tapioca": 35000,       # kg
    "Cardamom": 250,        # kg
    "Paddy": 3500,          # kg
}

def load_market_data(filepath):
    """
    Loads real market data from CSV and extracts relevant features.
    """
    df = pd.read_csv(filepath)
    # Ensure Date is datetime and extract month
    df['Date'] = pd.to_datetime(df['Date'])
    df['month'] = df['Date'].dt.month
    return df

def train_model(df):
    """
    Preprocesses categorical data using OrdinalEncoder and trains a RandomForestClassifier.
    Also calculates the average market price for each crop.
    """
    global clf, encoders, average_prices
    
    # Calculate average historical price per crop to estimate future revenue
    if 'Modal_Price' in df.columns:
        average_prices = df.groupby('Commodity')['Modal_Price'].mean().to_dict()
    
    # Categorical features to encode
    cat_features = ['District']
    
    df_encoded = df.copy()
    
    # Fit OrdinalEncoder for features to handle unknown districts gracefully
    enc_features = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
    df_encoded[cat_features] = enc_features.fit_transform(df[cat_features])
    encoders['features'] = enc_features
        
    # Fit LabelEncoder for the target column (Commodity)
    le_target = LabelEncoder()
    df_encoded['Commodity'] = le_target.fit_transform(df['Commodity'])
    encoders['Commodity'] = le_target
    
    # Define features (X) and target (y)
    X = df_encoded[['month', 'District']]
    y = df_encoded['Commodity']
    
    # Train RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)

def predict_top_crops(month, district, land_area, top_n=3):
    """
    Core prediction engine. Transforms string inputs, predicts probabilities, 
    calculates estimated revenue, and returns top matching crops.
    """
    global clf, encoders, average_prices
    
    if clf is None:
        raise ValueError("Model has not been trained yet.")
        
    # Transform inputs using the OrdinalEncoder. Unseen districts become -1.
    input_df = pd.DataFrame([[district]], columns=['District'])
    district_encoded = encoders['features'].transform(input_df)[0][0]
        
    # Create input DataFrame with feature names
    X_pred = pd.DataFrame([[month, district_encoded]], columns=['month', 'District'])
                          
    # Get probabilities for all classes
    probs = clf.predict_proba(X_pred)[0]
    
    # Get the class indices
    classes = clf.classes_
    
    # Sort indices by descending probability
    top_indices = np.argsort(probs)[::-1]
    
    results = []
    for idx in top_indices:
        prob = probs[idx]
        
        # Filter out 0% probability crops
        if prob > 0:
            # Transform integer class back to original string name
            crop_name = encoders['Commodity'].inverse_transform([classes[idx]])[0]
            
            avg_price = average_prices.get(crop_name, 100) 
            est_yield = YIELD_PER_HA.get(crop_name, 1000) * land_area
            # Divide by 100 as market prices in the dataset are typically per quintal (100kg)
            est_revenue = (est_yield * avg_price) / 100
            
            # --- Advanced Analysis from Dataset ---
            # Filter the raw data for this specific crop and month to find best market
            crop_data = df[(df['Commodity'] == crop_name) & (df['month'] == month)]
            
            if not crop_data.empty:
                # Find the market with the highest average modal price for this crop
                best_market_row = crop_data.groupby('Market')['Modal_Price'].mean().idxmax()
                min_hist = crop_data['Min_Price'].min()
                max_hist = crop_data['Max_Price'].max()
            else:
                best_market_row = "General Market"
                min_hist = avg_price * 0.9
                max_hist = avg_price * 1.1

            results.append({
                "crop": crop_name,
                "match_score": f"{prob * 100:.1f}%",
                "est_revenue": est_revenue,
                "avg_price": avg_price,
                "est_yield": est_yield,
                "best_market": best_market_row,
                "price_range": f"₹{min_hist:,.0f} - ₹{max_hist:,.0f}"
            })
            
            # Stop once we have reached the required number of top crops
            if len(results) == top_n:
                break
                
    return results

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_dir, "keralaCropDataset.txt")
    print(f"Loading real market dataset from {filepath}...")
    try:
        df = load_market_data(filepath)
        print(f"Dataset loaded successfully. {len(df)} records found.\n")
    except Exception as e:
        print(f"Failed to load data: {e}")
        exit(1)
    
    print("Training RandomForestClassifier...")
    train_model(df)
    print("Model trained successfully.\n")
    
    print("=" * 50)
    print("--- CROP PREDICTOR INTERACTIVE MODE ---")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 50)
    
    while True:
        try:
            month_input = input("\nEnter Month (1-12): ").strip()
            if month_input.lower() in ['exit', 'quit']:
                break
                
            if not month_input.isdigit() or not (1 <= int(month_input) <= 12):
                print("Invalid month. Please enter a number between 1 and 12.")
                continue
                
            district_input = input("Enter District (e.g., Idukki, Ernakulam): ").strip()
            if district_input.lower() in ['exit', 'quit']:
                break
                
            land_input = input("Enter Land Area (in hectares): ").strip()
            if land_input.lower() in ['exit', 'quit']:
                break
            try:
                land_area = float(land_input)
            except ValueError:
                print("Invalid land area. Please enter a valid number.")
                continue
                
            print(f"\nPredicting best crops and estimated profit for {district_input} in Month {month_input} on {land_area} hectares...")
            results = predict_top_crops(int(month_input), district_input, land_area)
            
            if not results:
                print("No suitable crops found.")
            else:
                # Comprehensive Output Table
                print(f"\n{'Rank':<5} | {'Crop Name':<15} | {'Best Market':<20} | {'Price Range/Qtl':<20} | {'Est. Revenue (₹)':<15}")
                print("-" * 85)
                for i, res in enumerate(results, 1):
                    print(f"{i:<5} | {res['crop']:<15} | {res['best_market']:<20} | {res['price_range']:<20} | ₹{res['est_revenue']:,.2f}")
                
                print("\n" + "="*85)
                print("DETAILED ANALYSIS FOR TOP RECOMMENDATION")
                print("="*85)
                top = results[0]
                print(f"Target Crop: {top['crop']}")
                print(f"Recommended Market: {top['best_market']} (Highest historical price in Month {month_input})")
                print(f"Projected Yield: {top['est_yield']:,.0f} units on {land_area} hectares")
                print(f"Estimated Revenue: ₹{top['est_revenue']:,.2f}")
                print(f"Market Volatility: {top['price_range']} (Min-Max Price per Quintal)")
                print("="*85)
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            
    print("\nExiting predictor. Goodbye!")
