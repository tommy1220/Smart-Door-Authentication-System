import base64
import boto3
import json
import cv2
import os
import time
import uuid
import sys

from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

sys.path.append("/opt") 
dynamodb = boto3.resource('dynamodb')
S3_Bucket_URL = 'https://smart-door-authentication.s3.amazonaws.com/'
OWNER_WEBPAGE = 'https://smart-door-authentication.s3.amazonaws.com/FrontEnd/WP1/index.html'
VISITOR_WEBPAGE = 'https://smart-door-authentication.s3.amazonaws.com/FrontEnd/WP2/index.html'
EMAIL_ADDRESS = 'cloudcomputing9223@gmail.com'
BUCKET = 'smart-door-authentication'


def lambda_handler(event, context):
    records = event["Records"]
    decoded_data = json.loads(base64.b64decode(records[0]["kinesis"]["data"]).decode("utf-8"))

    # INPUT TESTER
    print('event passed in is: ')
    print(event)
    print("Decoded data is :")
    print(decoded_data)
    
    visitor_frag_num = decoded_data['InputInformation']['KinesisVideo']['FragmentNumber']
    print('visitor_frag_num is:' + str(visitor_frag_num))
    
    if decoded_data['FaceSearchResponse'] == []:
        print('No found face in FaceSearchResponse')
        return;

    current_face = decoded_data['FaceSearchResponse'][0]
    # no matched face || matching low similarity
    if len(current_face['MatchedFaces']) == 0 or current_face['MatchedFaces'][0]['Similarity'] < 65:
        print('******** No matched face ... OR matched face(s) similarity too low ********* ')
        print('sending owner visitor info...')

        # get byte_chunk
        kinesis_client = boto3.client('kinesisvideo')
        response = kinesis_client.get_data_endpoint(StreamARN = 'arn:aws:kinesisvideo:us-east-1:306885591589:stream/KVS_T/1584912784204', APIName = 'GET_MEDIA_FOR_FRAGMENT_LIST')
        video_client = boto3.client('kinesis-video-archived-media', endpoint_url = response['DataEndpoint'])
        stream = video_client.get_media_for_fragment_list(StreamName = 'KVS_T', Fragments = [visitor_frag_num])
        byte_chunk = stream['Payload'].read()
        print('byte_chunk: ')
        print(byte_chunk)
        image_byte_data = convert_to_image_byte_data(byte_chunk)
        
        if image_byte_data != []:
            print('image_byte_data: ')
            s3_image_prefix = str(time.time()).split(".") 
            save_img_to_s3(image_byte_data, s3_image_prefix[0])
            send_email("dummyParameter", s3_image_prefix[0], BUCKET, str(datetime.now()))
        else:
            print('image_byte_data is empty: ')
            return;

    # face matched
    else:
        faceId = current_face['MatchedFaces'][0]['Face']['FaceId']
        print("Known face found: "+faceId)

        # search face in DB2
        visitor_dynamo_table = dynamodb.Table("visitors")
        response = visitor_dynamo_table.query(KeyConditionExpression=Key('faceId').eq(faceId))
        if response['Items'] != []:
            print("Found in vistor table: "+faceId)
            otp = retrieveOTP(faceId, "passcodes")
            if otp == [] or is_OTP_expired(faceId):
                if otp != [] and is_OTP_expired(faceId):
                    print("OTP expired with this faceID: "+faceId)
                    remove_expired_otp_and_faceID(faceId, otp)
                else:
                    print('no, face_id not in passcode table')
                    print("Not found in passcodes table: " + faceId)
                print('OTP is: ')
                new_OTP = get_new_OTP(faceId)
                insert_OTP_record(faceId, new_OTP)

                print('about to process new visitor photo')
                process_newVisitorPhoto(faceId)

                print('about to send new OTPs to verified visitor...')
                visitor_name = get_visitor_name(faceId)
                SNS_number = get_visitor_phone(faceId)
                send_SNS_text_message(SNS_number, visitor_name, new_OTP, VISITOR_WEBPAGE)
                
            
            # bcs once OTP expired, data entry with that face_id also deleted, then need to put face_id back on
            else: 
                print("faceID found in OTP dynamoDB is: "+faceId)
                print("OTP has not expired with this faceID: "+faceId)
                    
                
    return {
        'statusCode': 200,
        'body': json.dumps('Lambda Executed Successfully!')
    }


def process_newVisitorPhoto(faceId):
    current_time_strings = str(time.time()).split(".")
    photo_array = get_photo_array(faceId)

    # append new visitor photo to current visitor photo array
    appended_entry = dict()
    appended_entry['bucket'] = 'smart-door-authentication'
    appended_entry['objectKey'] = current_time_strings[0]
    appended_entry['createdTimestamp'] = str(datetime.now())
    photo_array.append(appended_entry)

    # update the photo array
    visitor_table = dynamodb.Table("visitors")
    response = visitor_table.update_item(
        Key = {
            'faceId': faceId
        },
        UpdateExpression = "set photos=:a",
        ExpressionAttributeValues = {
            ':a': photo_array
        },
        ReturnValues = "UPDATED_NEW"
    )
    print("photo array of visitor updated successful")
    print(response)


def convert_to_image_byte_data(byte_chunk):
    with open('/tmp/stream1.mkv', 'wb') as f:
        f.write(byte_chunk)
        f.close()
    try:
        fi = open("/tmp/stream1.mkv")
    except IOError:
        print("File not accessible")
    finally:
        fi.close()
    
    print(os.popen('df -h /tmp ; ls -lrt /tmp').read())
    cap = cv2.VideoCapture('/tmp/stream1.mkv')
    ret, frame = cap.read()
    if frame is not None:
        is_success, buffer = cv2.imencode(".jpg", frame)
        print(os.popen('df -h /tmp ; ls -lrt /tmp').read())
        cap.release()
        cv2.destroyAllWindows()
        return buffer.tobytes()
    else:
        return [];

def save_img_to_s3(img, file_name):
    s3_client = boto3.client('s3')
    if file_name is None:
        s3_client.put_object(
            Body=img, 
            Bucket=BUCKET, 
            Key=str(int(time.time()))+'.jpg', ContentType='image/jpeg', ACL='public-read')
    else:
        s3_client.put_object(
            Body = img, 
            Bucket=BUCKET,
            Key=file_name+'.jpg', ContentType='image/jpeg', ACL='public-read')

def is_OTP_expired(face_id):
    table_OTP = dynamodb.Table('passcodes')
    response = table_OTP.query(KeyConditionExpression=Key('faceId').eq(face_id))
    item_array = response['Items']
    record = item_array[0]
    timestamp = float(record['timestamp'])
    if float(time.time()) - timestamp <= 300:
        return False
    else:
        return True

def send_email(faceId, file_name, bucket_name, time_stamp):
    temp_OWNER_WEBPAGE = OWNER_WEBPAGE + '?faceId=' + faceId + '&file_name=' + file_name + '&bucket_name=' + bucket_name + '&time_stamp=' + time_stamp
    temp_S3_Bucket_URL = S3_Bucket_URL + file_name + '.jpg'
    print('sent url is:')
    print(temp_OWNER_WEBPAGE)
    print('image url:')
    print(temp_S3_Bucket_URL)
    email_content_html = """
    <html>
        <head>

        </head>

        <body>
            <p>
                Dear Smart Door Master,<br/>
                <br/>
                An unknown visitor has been detected:
                <br/>
            </p>


            <div align = "center">
                <img src=\"""" + temp_S3_Bucket_URL + """\", width="640px", height="480px">
            </div>


            <p>
                Are you to allow this person for permission on board? Please use following link to verify/deny this person.<br/>
            </p>


            <br/>

            <a href=\"""" + temp_OWNER_WEBPAGE + """"\">Unknown Visitor Permission Control Page</a>
        </body>
    </html>
             """


    SES_client = boto3.client('ses')
    response = SES_client.send_email(
        Source=EMAIL_ADDRESS,
        Destination={'ToAddresses': [EMAIL_ADDRESS,]},
        Message={
            'Subject': {
                'Charset': 'UTF-8',
                'Data': 'Unknown Visitor Detection Email'
            },
            'Body': {
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': 'Email Testing'
                },
                'Html': {
                    'Data': email_content_html,
                    'Charset': 'UTF-8'
                }
            }
        }
    )
    print('Response of SES email sending:')
    print(response)
    

def retrieveOTP(faceId, table_name):
    table_v = dynamodb.Table(table_name)
    response = table_v.query(KeyConditionExpression=Key('faceId').eq(faceId))
    item_array = response['Items']
    if item_array == []:
        return [];
    else:
        return item_array[0]['OTP']
        
def get_visitor_name(faceId):
    table_visitor = dynamodb.Table('visitors')
    response = table_visitor.query(KeyConditionExpression=Key('faceId').eq(faceId))
    item_array = response['Items']
    record = item_array[0]
    return record['name']

def get_visitor_phone(faceId):
    table_visitor = dynamodb.Table('visitors')
    response = table_visitor.query(KeyConditionExpression=Key('faceId').eq(faceId))
    item_array = response['Items']
    record = item_array[0]
    phone_num = '+1' + str(record['phoneNumber'])
    return phone_num
    
def insert_OTP_record(faceId, OTP):
    table_OTP = dynamodb.Table('passcodes')
    timestamp = time.time()
    response = table_OTP.put_item(
        Item={
            'faceId': faceId,
            'OTP': OTP,
            'timestamp': str(timestamp),
            'expireTimestamp':str(timestamp+300)
        }
    )
    print("Response of put OTP item in DB")
    print(response)
        
def remove_expired_otp_and_faceID(faceId, otp):
    dynamoDB_client = boto3.client('dynamodb')
    response = dynamoDB_client.delete_item(
        Key={
            'faceId': {
                'S': faceId
            },
            'OTP':{
                'S': otp
            }
        },
        TableName='passcodes'
    )
    print('Response of deleting an OTP from DB')
    print(response)

def get_new_OTP(faceId):
    OTP = str(uuid.uuid5(uuid.uuid4(), str(faceId)))
    OTP_strings = OTP.split('-')
    new_OTP = OTP_strings[0]
    while find_OTP_from_DB1(new_OTP):
        OTP = str(uuid.uuid5(uuid.uuid4(), str(faceId)))
        OTP_strings = OTP.split('-')
        new_OTP = OTP_strings[0]
    print('OTP:' + new_OTP)
    return new_OTP

def find_OTP_from_DB1(one_time_password):
    table = dynamodb.Table('passcodes')
    response = table.query(
        IndexName='OTP-index',
        KeyConditionExpression=Key('OTP').eq(one_time_password)
    )
    if response['Items'] == []:
        return False
    else:
        return True

def get_photo_array(faceId):
    table = dynamodb.Table('visitors')
    try:
        response = table.get_item(
            Key={
                'faceId': faceId
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        item = response['Item']
        photo_array = item['photos']
        print("GetItem successful")
        print(item)
        return photo_array
    
def send_SNS_text_message(phoneNumber, name, OTP, webpage):
    print('about to send SMS text msg')
    sns_client = boto3.client("sns", region_name='us-west-2')
    message = 'Dear Visitor, {}!\r\nYou have been verified by the Smart Door Master before! Please open the following URL in your browser and enter the password below:\r\n {}\r\nYour one-time-password is:\r\n{}\r\nEnjoy your visit!'.format(name, webpage, OTP)
    response = sns_client.publish(
        PhoneNumber = phoneNumber,
        Message = message
    )
    print('Response of sending SMS message:')
    print(response)
    
