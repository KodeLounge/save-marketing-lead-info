import logging
import boto3
import uuid
import json
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def save_marketing_lead_info(event, context):


  dynamodb = boto3.resource('dynamodb')
  leads_table = dynamodb.Table('kl-marketing-leads')
  request_params = json.loads(event["body"])

  with leads_table.batch_writer() as batch:
    batch.put_item(Item=lead_object_from_params(request_params["marketing_lead"]))
  
  send_mail(request_params["marketing_lead"])
  
  return {
    "isBase64Encoded": "true",
    "statusCode": 200,
    "headers" : {
      "Access-Control-Allow-Origin": os.environ.get("MARK_REQUEST_ORIGIN") or "*"
    },
    "body": json.dumps({'message':'Successfully saved.'})
  }


def send_mail(context):
  SENDER = os.environ.get('SENDER_SUPPORT_EMAIL') or "KL Marketing Enquiries <enquiries@kodelounge.com>"
  AWS_REGION = "us-west-2"
  SUBJECT = "New Lead from KL Marketing"
  CHARSET = 'UTF-8'
  recipients = os.environ.get('RECEIVER_EMAIL') or "sujit@kodelounge.com"
  recipients = recipients.split(',')
  recipients = [r.strip() for r in recipients]

  mail_body_params = {
    'name': context['name'],
    'subject': SUBJECT
  }
  
  if 'email' in context:
    mail_body_params['email'] = context['email']
  if 'phone' in context:
    mail_body_params['phone'] = context['phone']
  if 'message' in context:
    mail_body_params['message'] = context['message']

  BODY_HTML = email_content(mail_body_params)

  client = boto3.client('ses',region_name=AWS_REGION)

  try:
    response = client.send_email(
        Destination={
            'ToAddresses': recipients
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': BODY_HTML,
                },
                'Text': {
                    'Charset': CHARSET,
                    'Data': "Mail Text Here TODO",
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': SUBJECT,
            },
        },
        Source=SENDER
    )
  # Display an error if something goes wrong.	
  except ClientError as e:
      print(e.response['Error']['Message'])
  else:
      print("Email sent! Message ID:"),
      print(response['MessageId'])


def lead_object_from_params(lead_params):
  passed_parameters = set(lead_params.keys())
  allowed_keys = {'name','email','phone','message'}
  permitted_keys = passed_parameters & allowed_keys
  lead_params = {param : lead_params[param] for param in permitted_keys if lead_params[param] is not '' }
  lead_params["id"] = str(uuid.uuid4())
  return lead_params


def email_content(params):
  str = '''\
  <!DOCTYPE html>
    <html>
    <head>
      <meta content='text/html; charset=UTF-8' http-equiv='Content-Type'/>
      <title>{subject}</title>
    </head>
    <body>
    <div style="background:#F6F6F6; padding-bottom:20px; padding-top:20px; width: 100%">
      <div style="text-align: left;  background:#FFFFFF; padding:40px;  border-radius:2px; width: 70%; margin: auto;">
        <div style="font-size: 20px; color:#6A6A95;">Hello,</div>
        <div style="font-size: 16px; margin-top:11px; ">There was a recent enquiry from {name}.
        </div>

        <div style="font-size: 16px;  margin-top:13px;">Below are the details of the enquiry:<br><br>
          Name: {name}.<br>
  '''

  if 'email' in params and params['email'] is not '' :
      str += 'Email Address: <a href="mailto:{email}">{email}</a><br>'
  else :
      str += 'Phone: {phone}'

  if 'message' in params and params['message'] is not '' :
      str += 'Message: {message}'

  str+= ''' 
        </div>
        <div style="font-size: 16px;  margin-top:13px;">Thanks</div>
      </div>
    </body>
  </html>
  '''

  return str.format(**params)

