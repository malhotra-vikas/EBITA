import json
import csv

# Open the JSON file for reading
with open('data.json') as json_file:
    # Load the JSON data
    data = json.load(json_file)

# Open a CSV file for writing
with open('output.csv', 'w', newline='') as csv_file:
    # Create a CSV writer object
    csv_writer = csv.writer(csv_file)
    
    # Writing the headers (keys of the JSON)
    headers = data[0].keys()
    csv_writer.writerow(headers)
    
    # Writing the data
    for item in data:
        csv_writer.writerow(item.values())

