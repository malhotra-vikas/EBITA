import json
import re
import pandas as pd


# Load the data from a JSON file
with open('/Users/vikas/builderspace/EBITA/Lambdas/Utils/bizbuysell_1114_BBS.json', 'r') as file:
    ads_data = json.load(file)


# Create a DataFrame from the list of JSON objects
df = pd.DataFrame(ads_data)

# Assuming 'category' is a key in each JSON object, which seems to be your use case
category_counts = df['category'].value_counts()

# Assuming 'category' is a key in each JSON object
if 'category' in df.columns:
    category_counts = df['category'].value_counts()
    
    # Convert the Series to DataFrame for better handling
    category_counts_df = category_counts.reset_index()
    category_counts_df.columns = ['Category', 'Count']


    print(category_counts)
else:
    print("The 'category' column does not exist in the data.")