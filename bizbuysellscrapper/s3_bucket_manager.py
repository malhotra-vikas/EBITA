import boto3
from botocore.exceptions import ClientError
from scrapy.utils.project import get_project_settings
from bizbuysellscrapper.settings import custom_logger
settings = get_project_settings()

class S3BucketManager:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            's3',
            region_name=settings.get("AWS_REGION_NAME"),
            aws_access_key_id=settings.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=settings.get("AWS_SECRET_ACCESS_KEY"),
        )

    def create_bucket(self, region=None):
        if region:
            self.s3.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        else:
            self.s3.create_bucket(Bucket=self.bucket_name)

    def head_bucket(self, bucket_name):
        try:
            self.s3.head_bucket(Bucket=bucket_name)
            return True  # Bucket exists
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False  # Bucket does not exist
            else:
                # Other error occurred, handle as needed
                raise

    def get_or_create_bucket(self, region=None):
        # Check if the bucket exists
        if self.head_bucket(bucket_name=self.bucket_name):
            return self.bucket_name
        else:
            # Create the bucket
            self.create_bucket(region=region)
            return self.bucket_name

    def put_object(self, bucket_name, key, body):
        self.s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=body
        )
        custom_logger.info("Json file added successfully in s3 bucket", bucket_name, key)
        

    def head_object(self, bucket_name,object_name):
        try:
            response = self.s3.head_object(Bucket=bucket_name, Key=object_name)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                custom_logger.error(f"Object '{object_name}' does not exist in the bucket '{self.bucket_name}'")
            else:
                custom_logger.error("An error occurred:", e)
            return None

    def list_objects(self):
        response = self.s3.list_objects_v2(Bucket=self.bucket_name)
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        else:
            return []
        
    def get_object(self, bucket_name, object_name):
        try:
            response = self.s3.get_object(Bucket=bucket_name, Key=object_name)
            object_content = response['Body'].read()
            return object_content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                custom_logger.error(f"Object '{object_name}' does not exist in the bucket '{self.bucket_name}'")
            else:
                custom_logger.error("An error occurred:", e)
            return None

    def upload_file(self, file_name, object_name=None):
        if not object_name:
            object_name = file_name
        self.s3.upload_file(file_name, self.bucket_name, object_name)

    def download_file(self, object_name, file_name):
        self.s3.download_file(self.bucket_name, object_name, file_name)

    def move_object(self, source_key, destination_bucket_name, destination_key):
        try:
            # Copy the object
            self.s3.copy_object(
                CopySource={'Bucket': self.bucket_name, 'Key': source_key},
                Bucket=destination_bucket_name,
                Key=destination_key
            )

            # Delete the original object
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=source_key
            )

            custom_logger.info(f"Object moved successfully from '{self.bucket_name}/{source_key}' to '{destination_bucket_name}/{destination_key}'")
            return True
        except ClientError as e:
            custom_logger.error(f"An error occurred: {e}")
            return False