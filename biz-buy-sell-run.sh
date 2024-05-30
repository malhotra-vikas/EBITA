#!/bin/bash

# Navigate to the Scrapy project directory
cd /home/ubuntu/EBITA

 # Activate the virtual environment
source venv/bin/activate

# Run the Scrapy spider
scrapy crawl bizbuysell >> /home/ubuntu/EBITA/cronjob.log 2>&1

echo "Job completed successfully."

# Send an email notification
SUBJECT="Cron Job Completed"
TO="malhotra.vikas@gmail.com, arora.silky@gmail.com"

MESSAGE="The BizBuySell cron job that runs at 2 AM has completed successfully."

echo $MESSAGE | mail -s "$SUBJECT" $TO

echo "Notification email sent to $TO."

#scrapy crawl bizbuysell >> /home/ubuntu/project/cronjob.log 2>&1