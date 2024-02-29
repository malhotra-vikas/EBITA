ScrappedDataSchema = dict(
    KeySchema=[
        {"AttributeName": "ad_id", "KeyType": "HASH"}  # Partition key
    ],
    AttributeDefinitions=[
        {"AttributeName": "ad_id", "AttributeType": "S"},
    ],
)