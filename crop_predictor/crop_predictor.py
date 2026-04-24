import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder

# Global variables to store our trained model and encoders
clf = None
encoders = {}

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
    """
    global clf, encoders
    
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

def predict_top_crops(month, district, top_n=3):
    """
    Core prediction engine. Transforms string inputs, predicts probabilities, 
    and returns top matching crops.
    """
    global clf, encoders
    
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
            results.append({
                "crop": crop_name,
                "match_score": f"{prob * 100:.1f}%"
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
                
            print(f"\nPredicting best crops for {district_input} in Month {month_input}...")
            results = predict_top_crops(int(month_input), district_input)
            
            if not results:
                print("No suitable crops found.")
            else:
                for i, res in enumerate(results, 1):
                    print(f"  {i}. {res['crop']} (Confidence: {res['match_score']})")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            
    print("\nExiting predictor. Goodbye!")
