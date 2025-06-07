import json
import boto3

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ugawsdemotable')  

# Common CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST'
}

def lambda_handler(event, context):
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    # Parse JSON body
    raw_body = event.get('body')
    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid JSON format in request body'})
        }

    print("DEBUG BODY:", body)

    # Validate required fields
    message = body.get('message')
    notification_type = body.get('type')
    if not message or not notification_type:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': "Missing 'message' or 'type' in request body"})
        }

    # Ensure SMS attributes (once per Lambda invocation)
    if notification_type == 'sms':
        try:
            sns.set_sms_attributes(
                attributes={'DefaultSMSType': 'Transactional'}
            )
        except Exception as e:
            print("Warning: Unable to set SMS attributes:", e)

    try:
        # Send notification
        if notification_type == 'sms':
            sns_response = sns.publish(
                PhoneNumber='+233549853180',
                Message=message
            )
            custom_message = f"SMS Sent: '{message}'"

        elif notification_type == 'email':
            sns_response = sns.publish(
                TopicArn='arn:aws:sns:us-east-1:792527467644:todoAppSNS',
                Message=message,
                Subject='Notification'
            )
            custom_message = f"Email Sent: '{message}'"

        else:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Invalid notification type'})
            }

        # Store message in DynamoDB
        table.put_item(
            Item={
                'message_id': sns_response['MessageId'],
                'msg': message,
                'notification_type': notification_type
            }
        )

        # Successful response
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'message': custom_message,
                'SNSResponse': sns_response
            })
        }

    except Exception as e:
        print("Publish error:", e)
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(e)})
        }