import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_client():
    """Initialize and return Razorpay client"""
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        logger.debug("Initialized Razorpay client with key_id=%s", settings.RAZORPAY_KEY_ID)
        print("[DEBUG] Razorpay client initialized")
        return client
    except Exception as e:
        logger.exception("Failed to initialize Razorpay client: %s", str(e))
        print("[ERROR] Razorpay client init failed:", str(e))
        raise

def create_order(amount_paise: int, currency='INR', receipt=None, notes=None):
    """
    Create a Razorpay order
    
    Args:
        amount_paise: Amount in paise (smallest currency unit)
        currency: Currency code (default: INR)
        receipt: Receipt ID for reference
        notes: Additional metadata
        
    Returns:
        dict: Razorpay order response
    """
    client = get_client()
    data = {"amount": amount_paise, "currency": currency}
    if receipt:
        data['receipt'] = receipt
    if notes:
        data['notes'] = notes
    
    try:
        logger.debug("Calling razorpay.order.create with data=%s", data)
        print("[DEBUG] Calling razorpay.order.create", data)
        order = client.order.create(data)
        logger.debug("Razorpay order created: %s", order.get('id'))
        print("[DEBUG] Razorpay order created id:", order.get('id'))
        return order
    except Exception as e:
        logger.error("Failed to create Razorpay order: %s", str(e))
        print("[ERROR] Failed to create Razorpay order:", str(e))
        raise

def verify_payment_signature(payload: dict) -> bool:
    """
    Verify payment signature from Razorpay
    
    Args:
        payload: Dict containing razorpay_order_id, razorpay_payment_id, razorpay_signature
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    client = get_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": payload['razorpay_order_id'],
            "razorpay_payment_id": payload['razorpay_payment_id'],
            "razorpay_signature": payload['razorpay_signature']
        })
        logger.debug("Payment signature verified successfully")
        print("[DEBUG] verify_payment_signature success for", payload.get('razorpay_payment_id'))
        return True
    except Exception as e:
        logger.warning("Razorpay signature verification failed: %s", str(e))
        print("[WARN] verify_payment_signature failed:", str(e))
        return False