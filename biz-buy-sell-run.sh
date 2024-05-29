#!/bin/bash

# Navigate to the Scrapy project directory
cd /home/ubuntu/EBITA

 # Activate the virtual environment
source venv/bin/activate

# Run the Scrapy spider
scrapy crawl bizbuysell >> /home/ubuntu/EBITA/cronjob.log 2>&1

#scrapy crawl bizbuysell >> /home/ubuntu/project/cronjob.log 2>&1