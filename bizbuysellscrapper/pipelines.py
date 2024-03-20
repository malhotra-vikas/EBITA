# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json
from bizbuysellscrapper.db import DynamoDBManager
from bizbuysellscrapper.schema import ScrappedDataSchema
from bizbuysellscrapper.s3_bucket_manager import S3BucketManager
from scrapy.utils.project import get_project_settings

settings = get_project_settings()

class DynamoDBPipeline:
    table_name = settings.get("DYNAMODB_TABLE_NAME")

    def open_spider(self, spider):
        self.dynamodb = DynamoDBManager(self.table_name)
        self.table = self.dynamodb.get_table(ScrappedDataSchema)

    def process_item(self, item, spider):
        self.dynamodb.put_item(dict(item).get("businessOpportunity"))
        return item
    

class S3Pipeline:
    output_bucket_name = settings.get("OUTPUT_S3_BUCKET_NAME")

    def __init__(self):
        self.s3_manager = S3BucketManager(self.output_bucket_name)  
        self.items = [] 

    def get_or_create_bucket(self):
        # Use the S3 manager to get or create the bucket
        return self.s3_manager.get_or_create_bucket()

    def process_item(self, item,spider):
        # Extract URL from the item 
        self.items.append(dict(item).get("businessOpportunity"))

        self.save_item(self.items,spider)


    def save_item(self, item_list, spider):
        # Get or create the bucket
        bucket = self.get_or_create_bucket()
         
        # Put the item into the bucket
        self.s3_manager.put_object(
            bucket_name=bucket,
            key=f"{spider.name}_{item_list[0]['ad_id']}.json",
            body=json.dumps(item_list)
        )
        
                
        return item_list
