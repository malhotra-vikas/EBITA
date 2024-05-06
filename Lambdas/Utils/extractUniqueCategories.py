import json
import re

# Load the data from a JSON file
with open('/Users/vikas/builderspace/EBITA-2/Lambdas/Utils/bizbuysell_2041937_BBS.json', 'r') as file:
    ads_data = json.load(file)

# Function to clean up the category name
def clean_category(category: str) -> str:
    return re.sub(r'\s+For Sale$', '', category)

# Use a set to collect unique categories, cleaning each category name
unique_categories = {clean_category(ad['category']) for ad in ads_data if 'category' in ad and ad['category']}

# Convert the set to a sorted list for better organization
sorted_categories = sorted(unique_categories)

# Print the cleaned unique categories
print(sorted_categories)
