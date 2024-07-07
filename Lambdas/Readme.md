### Messaging Lambda Setup

# Bundle with Twilio
ca Lambdas
pip install twilio --target=./packages
zip -r twillioMessagingLambda.zip ./packages twillioMessagingLambda.py

Ensure that the ENV variables are setupo
1. PYTHONPATH = /var/task/packages
2. TWILIO_ACCOUNT_SID
3. TWILIO_AUTH_TOKEN
4. TWILIO_PHONE_NUMBER
