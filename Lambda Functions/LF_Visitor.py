import time
import boto3
from boto3.dynamodb.conditions import Key

OTP_TABLE = 'passcodes'
VISITOR_TABLE = 'visitors'
dynamodb = boto3.resource('dynamodb')
FIVE_MINUTE = 300

def lambda_handler(event, context):
    # TODO implement
    print('input: ')
    print(event)
    OTP = event['OTP']
    print('OTP: ')
    print(OTP)
    
    item_array = query_OTP(OTP)
    
    if item_array != []:
        faceId = item_array[0]['faceId']
        timestamp = float(item_array[0]['timestamp'])

        if float(time.time()) - timestamp <= FIVE_MINUTE:
            name = query_visitor_information(faceId)
            return "Hi, "+name+"!\r\n Welcome!"
        delete_OTP(faceId, OTP)
    return "Permission denied!"
    
def query_visitor_information(faceId):
    table = dynamodb.Table(VISITOR_TABLE)
    resp = table.query(
        KeyConditionExpression=Key('faceId').eq(faceId)
    )
    print("VISITOR information: ")
    print(resp)
    return resp['Items'][0]['name']

def query_OTP(OTP):
    table = dynamodb.Table(OTP_TABLE)
    response = table.query(
        IndexName='OTP-index',
        KeyConditionExpression=Key('OTP').eq(OTP)
    )
    print('query result:')
    print(response)
    return response['Items']
    
def delete_OTP(faceId, OTP):
    dynamoDB_client = boto3.client('dynamodb')
    response = dynamoDB_client.delete_item(
        Key={
            'faceId': {
                'S': faceId,
            },
            'OTP':{
                'S': OTP
            }
        },
        TableName=OTP_TABLE
    )
    print('The response: ')
    print(response)