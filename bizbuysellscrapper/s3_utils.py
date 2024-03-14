from bizbuysellscrapper.s3_bucket_manager import S3BucketManager
import csv
import json

def get_file_format(bucket_name, file_key):
    s3 = S3BucketManager(bucket_name)
    response = s3.head_object(bucket_name, file_key)
    content_type = response.get('ContentType', '')
    if content_type:
        if content_type == 'application/json':
            return 'json'
        elif content_type == 'text/csv':
            return 'csv'
        elif content_type.startswith('text/plain'):
            return 'txt'
    else:
        file_extension = file_key.split('.')[-1].lower()
        if file_extension == 'json':
            return 'json'
        elif file_extension == 'csv':
            return 'csv'
        elif file_extension == 'txt':
            return 'txt'
    return None


def get_input_urls_from_s3(bucket_name, file_key, file_format):
    s3 = S3BucketManager(bucket_name)
    obj = s3.get_object(bucket_name, file_key)
    content = obj.decode('utf-8')

    input_urls = []
    if file_format == 'csv':
        reader = csv.reader(content.splitlines())
        input_urls = [row[0] for row in reader]
    elif file_format == 'txt':
        input_urls = content.split('\n')
    elif file_format == 'json':
        data = json.loads(content)
        if isinstance(data, list):
            input_urls = data
        elif isinstance(data, dict):
            input_urls = data.get('urls', [])
    else:
        raise ValueError("Unsupported file format")

    return input_urls

