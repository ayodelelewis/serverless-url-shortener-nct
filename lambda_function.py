import json
import boto3
import os
import hashlib
import time

s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']
BASE_URL = os.environ['BASE_URL']

def lambda_handler(event, context):
    route = event.get('routeKey', event.get('httpMethod'))
    
    # For HTTP API v2 (Payload format 2.0)
    if route == 'POST /shorten' or event.get('httpMethod') == 'POST':
        return create_short_url(event)
    elif route == 'GET /stats' or event.get('httpMethod') == 'GET':
        return get_stats()
    
    return response(200, {'message': 'URL Shortener API'})

def create_short_url(event):
    try:
        # Parse body (handle different API Gateway versions)
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        long_url = body.get('url')
        
        if not long_url or not long_url.startswith('http'):
            return response(400, {'error': 'Valid URL required (must start with http)'})
        
        # Generate short code
        short_code = hashlib.sha256(f"{long_url}{time.time()}".encode()).hexdigest()[:8]
        
        # Store with redirect metadata
        s3.put_object(
            Bucket=BUCKET,
            Key=short_code,
            WebsiteRedirectLocation=long_url,
            ContentType='text/html',
            Metadata={
                'original-url': long_url,
                'created': str(int(time.time()))
            }
        )
        
        return response(201, {
            'shortUrl': f"{BASE_URL}/{short_code}",
            'shortCode': short_code,
            'originalUrl': long_url
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': str(e)})

def get_stats():
    try:
        objects = s3.list_objects_v2(Bucket=BUCKET, MaxKeys=20)
        urls = []
        
        if 'Contents' in objects:
            for obj in objects['Contents']:
                try:
                    metadata = s3.head_object(Bucket=BUCKET, Key=obj['Key'])
                    urls.append({
                        'shortCode': obj['Key'],
                        'originalUrl': metadata.get('Metadata', {}).get('original-url', 'N/A')[:50] + '...',
                        'created': metadata.get('Metadata', {}).get('created', 'N/A')
                    })
                except:
                    pass
        
        return response(200, {'urls': urls})
        
    except Exception as e:
        return response(500, {'error': str(e)})

def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS'
        },
        'body': json.dumps(body)
    }