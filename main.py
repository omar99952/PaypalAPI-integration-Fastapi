from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
import paypalrestsdk
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# PayPal configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # or "live" for production
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

@app.post("/create-order")
async def create_order(request: Request):
    try:
        body = await request.json()
        cart = [{
                "product_id": 1,  # Example product ID
                "name": 'Sample Product',
                "price": 0.01,
                "currency": 'CAD'
            }]#body.get('cart', [])

        if not cart:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        # Summarize cart total amount
        total_amount = sum(item['price'] for item in cart)
        
        # Ensure total_amount is not zero or negative
        if total_amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid total amount.")

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [{
                "amount": {
                    "total": 100.00,#f"{total_amount:.2f}",
                    "currency": "USD"  # Change currency to EUR
                },
                "description": "This is the payment transaction description."
            }]

        ,
            "redirect_urls": {
                "return_url": "http://localhost:8000/execute-payment",
                "cancel_url": "http://localhost:8000/"
            },
            "application_context": {
                "brand_name": "ASAS For Furniture",
                # "shipping_preference": "NO_SHIPPING",
                # "user_action":"PAY_NOW"
            }
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = str(link.href)
                    logger.info({"approval_url": approval_url})
                    return {"approval_url": approval_url, "paymentID": payment.id}
        
        logger.error(f"PayPal Payment Creation Error: {payment.error}")
        raise HTTPException(status_code=400, detail=payment.error)

    except Exception as e:
        logger.error(f"An error occurred while creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/execute-payment/")
async def execute_payment(paymentId: str = Query(...), PayerID: str = Query(...)):
    try:
        payment = paypalrestsdk.Payment.find(paymentId)
        logger.info({"payerId": PayerID})

        if payment.execute({"payer_id": PayerID}):
            logger.info("Payment executed successfully")
            return {"status": "Payment executed successfully"}
        
        error_details = payment.error
        logger.error(f"PayPal Payment Execution Error: {error_details}")
        raise HTTPException(status_code=400, detail=error_details)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/paypal/webhook")
async def handle_webhook(request: Request):
    try:
        body = await request.json()
        event_type = body.get("event_type")

        if event_type == "PAYMENT.SALE.COMPLETED":
            # Handle payment sale completed event
            logger.info("Payment sale completed event received")
            # Implement your logic here
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"An error occurred while handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("static/index.html") as f:
            return HTMLResponse(content=f.read())
    
    except Exception as e:
        logger.error(f"An error occurred while reading index: {e}")
        raise HTTPException(status_code=500, detail=str(e))
