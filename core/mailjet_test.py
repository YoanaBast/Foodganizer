"""
This call sends a message to one recipient.
"""
from mailjet_rest import Client
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ['MAIL_API']
api_secret = os.environ['MAIL_SECRET']
mailjet = Client(auth=(api_key, api_secret), version='v3.1')
data = {
  'Messages': [
				{
						"From": {
								"Email": "pilot@mailjet.com",
								"Name": "Mailjet Pilot"
						},
						"To": [
								{
										"Email": "passenger1@mailjet.com",
										"Name": "passenger 1"
								}
						],
						"Subject": "Your email flight plan!",
						"TextPart": "Dear passenger 1, welcome to Mailjet! May the delivery force be with you!",
						"HTMLPart": "<h3>Dear passenger 1, welcome to <a href=\"https://www.mailjet.com/\">Mailjet</a>!</h3><br />May the delivery force be with you!"
				}
		]
}
result = mailjet.send.create(data=data)
print (result.status_code)
print (result.json())