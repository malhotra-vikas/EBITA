import json

def debt_calculator_handler(event, context):
    print("Event Starting")

    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "content-type": "application/json"
        },
        "isBase64Encoded": False,
        "body": ""
    }

    print("Event body is", json.dumps(event.get("body")))

    body_data = json.loads(event.get("body", "{}"))

    # Extract details from the request body
    revenue = body_data.get("revenue")  # Dollars
    cash_flow = body_data.get("cashFlow")  # Dollars
    ebitda = body_data.get("ebitda")  # Dollars
    price = body_data.get("price")  # Dollars
    downpayment = body_data.get("downpayment")  # Dollars
    interest = body_data.get("interest")  # Interest Percentage
    termYears = body_data.get("term")  # Term in Years

    if not all([revenue, cash_flow, ebitda, price, downpayment, interest, termYears]):
        response["body"] = "Validation Error - User missing required fields"
        response["statusCode"] = 500
        print("Response from calculator Lambda: 1", json.dumps(response))
        return response

    # Calculate necessary values
    ebitda_monthly = ebitda / 12
    ebitda_x = price / ebitda
    loan_amount = price - downpayment
    monthly_interest = interest / 12 / 100
    term_months = termYears * 12
    cfMargin = (cash_flow / revenue) * 100

    print("calcul;ating for:", loan_amount)
    print("calcul;ating for:", monthly_interest)
    print("calcul;ating for:", term_months)

    # Calculate PMT
    pmt = (loan_amount * monthly_interest / (1 - (1 + monthly_interest) ** -term_months))*12

    net_cash_flow = cash_flow - pmt

    debt_service_coverage = cash_flow / pmt
    
    # Calculate Payback Period
    payback_period = (revenue * 0.1) / (net_cash_flow / 12)

    # Construct the response body
    response_body = {
        "message": "Lambda function executed successfully",
        "data": {
            "revenue": revenue,
            "cash_flow": cash_flow,
            "ebitda": ebitda,
            "price": price,
            "downpayment": downpayment,
            "interest": interest,
            "loan_amount": loan_amount,
            "term_years": termYears,
            "term_months": term_months,
            "annual_debt_service": round(pmt),
            "net_cash_flow": round(net_cash_flow),
            "CF_margin": round(cfMargin),
            "debt_service_coverage": round(debt_service_coverage, 1),
            "payback_period": round(payback_period, 1)  # Rounded to 2 decimal places
        }
    }

    # Set the response body and return the response
    response["body"] = json.dumps(response_body)
    print("Response from calculator Lambda:", json.dumps(response))
    return response
