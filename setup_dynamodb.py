import boto3
from dotenv import load_dotenv
import os

load_dotenv()

AWS_REGION     = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')

dynamodb = boto3.resource(
    'dynamodb',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def create_tables():
    tables = [
        {
            'TableName': 'stocker_users',
            'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'email', 'AttributeType': 'S'}],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'stocker_stocks',
            'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'stocker_transactions',
            'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'stocker_portfolio',
            'KeySchema': [
                {'AttributeName': 'user_id',  'KeyType': 'HASH'},
                {'AttributeName': 'stock_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id',  'AttributeType': 'S'},
                {'AttributeName': 'stock_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
    ]

    for t in tables:
        try:
            dynamodb.create_table(**t)
            print(f"✅ Table created: {t['TableName']}")
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            print(f"⚠️  Table already exists: {t['TableName']}")
        except Exception as e:
            print(f"❌ Error creating {t['TableName']}: {e}")

if __name__ == '__main__':
    print("Creating DynamoDB tables...")
    create_tables()
    print("Done!")