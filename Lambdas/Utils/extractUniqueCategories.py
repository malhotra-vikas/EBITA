import json
import pandas as pd

# Load the data from a JSON file
with open('/Users/vikas/builderspace/EBITA/Lambdas/Utils/bizbuysell_20240528.json', 'r') as file:
    ads_data = json.load(file)

    # Create a DataFrame from the list of JSON objects
    df = pd.DataFrame(ads_data)
        # Get the counts of each category
    category_counts = df['category'].value_counts()

        # Convert the Series to DataFrame for better handling
    category_counts_df = category_counts.reset_index()
    category_counts_df.columns = ['Category', 'Count']

    # Calculate the total number of listings
    total_listings = len(df)

        # Print the category counts and total number of listings
    print(category_counts_df)
    print(f"\nTotal number of listings: {total_listings}")

# Check if 'category' is a key in each JSON object
