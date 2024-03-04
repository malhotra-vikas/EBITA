#!/bin/bash

# Activate the virtual environment
#source /home/ubuntu/project/venv/bin/activate

# Navigate to the Scrapy project directory
cd /home/ubuntu/project/EBITA

# Run the Scrapy spider
/home/ubuntu/project/venv/bin/scrapy crawl bizbuysell >> /home/ubuntu/project/cronjob.log 2>&1

#scrapy crawl bizbuysell >> /home/ubuntu/project/cronjob.log 2>&1

