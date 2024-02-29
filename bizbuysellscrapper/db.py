from typing import Any
import boto3
import os
from scrapy.utils.project import get_project_settings
from bizbuysellscrapper.settings import custom_logger

settings = get_project_settings()

class DynamoDBManager:
    def __init__(self, table_name):
        self.table_name = table_name
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=settings.get("AWS_REGION_NAME"),
            aws_access_key_id=settings.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=settings.get("AWS_SECRET_ACCESS_KEY"),
        )
        self.table = self.dynamodb.Table(table_name)
    
    def create_table(self, KeySchema, AttributeDefinitions):
        table = self.dynamodb.create_table(
            TableName=self.table_name,
            KeySchema=KeySchema,
            AttributeDefinitions=AttributeDefinitions,
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=self.table_name)
        return table

    def get_table(self, schema):
        existing_tables = [table.name for table in self.dynamodb.tables.all()]
        if self.table_name not in existing_tables:
            custom_logger.info("creating table ", self.table_name)
            self.create_table(**schema)
        self.table = self.dynamodb.Table(self.table_name)
    
    def put_item(self, item):
        self.table.put_item(Item=item)
        custom_logger.info("Item added successfully.")
    
    def get_item(self, key):
        response = self.table.get_item(Key=key)
        item = response.get('Item')
        return item
    
    def update_item(self, key, update_expression, expression_attribute_values):
        self.table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        custom_logger.info("Item updated successfully.")
    
    def delete_item(self, key):
        self.table.delete_item(Key=key)
        custom_logger.info("Item deleted successfully.")
    
    def delete_table(self):
        self.table.delete()
        custom_logger.info(f"Table '{self.table_name}' deleted successfully.")
