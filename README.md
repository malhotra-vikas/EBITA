## buz_scrapper

## Step 1: Upload Input File to S3 Bucket

1. Login to AWS account, and go to S3 service.
2. Upload an input text file containing URLs to the S3 bucket named "scraper-input-bucket".

## Step 2: Go to server 

1. Run ssh command on your local terminal:-

```
ssh -i "/path to pem key/" ubuntu@ec2-18-204-157-214.compute-1.amazonaws.com
```

2. go to project folder using command :-
com
```
cd project/buz_scrapper/bizbuysellscrapper/
```
## Step 3: Running the Application mannually
1. To start the application mannually, run the following command:

For BizBuySell:
    ```
    scrapy crawl bizbuysell
    ```

For Business for sale:
    ```
    scrapy crawl bussinessforsale
    ```

## Step 4: Crontab setup configuration for running application automatically

1. I've set up a cronjob to execute the script. Currently, it's scheduled to run once a day.
2. To adjust the configuration, use the following command:
   ```
   crontab -e

    ```
3. Edit the cron tab to modify the schedule according to your requirements.
4. Make any necessary changes and save the file to apply the new configuration.


## Step 5: To check output on AWS services

After running the command, follow these steps:

### Dynamodb
1. After some time,go to AWS S3 service and verify the scraped data in the DynamoDB table named my_scraped_data.

### S3 bucket
1. Additionally, check the output files in the designated S3 output bucket named "output-scraper-bucket".

3. If data is successfully scraped, your application is functioning correctly.


## Setup for the .env file inside the project directory
1. Go the project folder that is EBITA
2. Create the .env file here with this command:
    ```
    touch .env
    ```
3. Now after create the env file store all the variables inside it, with this command or store mannually:
    ```
    nano .env
    ```
4. After the stored all the variables it will pick all the variables automatically from the env file.