import json
import boto3
import uuid
import time
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
db_resource = boto3.resource('dynamodb')

VISITOR_WEBPAGE = 'https://smart-door-authentication.s3.amazonaws.com/FrontEnd/WP2/index.html'
TABLE_VISITOR_NAME = 'visitors'
TABLE_OTP_NAME = 'passcodes'
COLLECTION_ID = 'faces'
# {
#   "name": "Hitesh Acharya",
#   "faceId": "d5bd7e1f-291a-4c10-aea1-da907c2272ca",
#   "phoneNumber": "4143341784",
#   "objectKey": "1586365366",
#   "bucket": "smart-door-authentication",
#   "createdTimestamp": "2020-04-08%2017:02:46.928037",
#   "access_denied": "0"
# }

# {
#   "name": "Hitesh Acharya",
#   "faceId": "d5bd7e1f-291a-4c10-aea1-da907c2272ca",
#   "phoneNumber": "4143341784",
#   "objectKey": "1586365366",
#   "bucket": "smart-door-authentication",
#   "createdTimestamp": "2020-04-08%2017:02:46.928037",
#   "access_denied": "1"
# }

# https://smart-door-authentication.s3.amazonaws.com/FrontEnd/WP1/index.html
# ?faceId=d5bd7e1f-291a-4c10-aea1-da907c2272ca
# &file_name=1586365366
# &bucket_name=smart-door-authentication
# &time_stamp=2020-04-08%2017:02:46.928037

def lambda_handler(event, context):
    
    print('event: ')
    print(event) 
    objectKey = event['objectKey']
    bucket = event['bucket']
    createdTimestamp = event['createdTimestamp']
    
    if event['access_denied'] and int(event['access_denied']) == 0 and event['name'] and event['phoneNumber']:
        faceId = add_visitor_faceID_to_collection(bucket, objectKey)
        put_visitor(faceId, event['name'], event['phoneNumber'], objectKey, bucket, createdTimestamp)
        OTP = create_new_OTP(faceId)
        send_message('+1'+str(event['phoneNumber']), event['name'], OTP, VISITOR_WEBPAGE)
        put_OTP_to_otpTable(faceId, OTP)
        print('store user information')
        return "Visitor faceID collected, visitor added to DB2, message sent !"
    else: 
        remove_visitor_photo_from_S3(bucket, objectKey)
        if event['access_denied'] and int(event['access_denied']) == 1:
            send_SMS_Denied_message(event['phoneNumber'], event['name'])
            return "Deny visitor\'s accesss!"
            print('visitor denied!')
        return "Parameter error! Please enter all information provided!"
        

def put_visitor(ID, name, phoneNumber, objectKey, bucket, timestamp):
    table_visitor = db_resource.Table(TABLE_VISITOR_NAME)
    objectKey = str(objectKey) + '.jpg'
    response = table_visitor.put_item(
        Item={
            'faceId': ID,
            'name': name,
            'phoneNumber': phoneNumber,
            'photos': [
                {
                    'objectKey': objectKey,
                    'bucket': bucket,
                    'createdTimestamp': str(timestamp)
                }
            ]
        }
    )
    print('response:')
    print(response)

def add_visitor_faceID_to_collection(bucket,objectKey):
    rekognition_client = boto3.client('rekognition')
    response = rekognition_client.index_faces(
        CollectionId = COLLECTION_ID,
        Image={'S3Object': {'Bucket': bucket, 'Name': objectKey + '.jpg', } },
        DetectionAttributes=['ALL'],
        MaxFaces=1,
        QualityFilter='AUTO'
    )
    faceId = response['FaceRecords'][0]['Face']['FaceId']
    print('faceID: ' + str(faceId))
    return faceId
    
def put_OTP_to_otpTable(faceId, OTP):
    table_OTP = db_resource.Table(TABLE_OTP_NAME)
    timestamp = time.time()
    response = table_OTP.put_item(
        Item={
            'faceId': faceId,
            'OTP': OTP,
            'timestamp': str(timestamp),
            'expireTimestamp':str(timestamp+300)
        }
    )
    print("response: ")
    print(response)
    
def send_message(phoneNumber, name, OTP, webpage):
    print('about to send SMS text msg')
    sns_client = boto3.client("sns", region_name='us-west-2')
    message = 'Hello, {}!\r\nYou are allowed to enter. Please open the following URL in your browser and enter the password below:\r\n {}\r\nYour one-time-password is:\r\n{}\r\nEnjoy your visit!'.format(name, webpage, OTP)
    response = sns_client.publish(
        PhoneNumber=phoneNumber,
        Message=message
    )
    print('response:')
    print(response)
    
def send_SMS_Denied_message(phoneNumber, name):
    print('about to send SMS denied text msg')
    sns_client = boto3.client("sns", region_name='us-west-2')
    message = 'Sorry, you are not granted with any permission to enter the smart door.'
    response = sns_client.publish(
        PhoneNumber=phoneNumber,
        Message=message
    )
    print('response:')
    print(response)    
    
def create_new_OTP(faceId):
    OTP = str(uuid.uuid5(uuid.uuid4(), str(faceId)))
    OTP_strings = OTP.split('-')
    new_OTP = OTP_strings[0]
    while search_OTP(new_OTP):
        OTP = str(uuid.uuid5(uuid.uuid4(), str(faceId)))
        OTP_strings = OTP.split('-')
        new_OTP = OTP_strings[0]
    print('OTP:' + new_OTP)
    return new_OTP

def remove_visitor_photo_from_S3(bucket_name, object_key):
    s3 = boto3.resource('s3')
    object_summary = s3.ObjectSummary(bucket_name, object_key)
    response = object_summary.delete()
    print("response:")
    print(response)
    
def search_OTP(OTP):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('passcodes')
    response = table.query(
        IndexName='OTP-index',
        KeyConditionExpression=Key('OTP').eq(OTP)
    )
    if response['Items'] == []:
        return False
    else:
        return True

