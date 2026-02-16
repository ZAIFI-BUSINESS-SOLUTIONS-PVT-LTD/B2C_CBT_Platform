"""
Google Play Billing Service

Handles verification of Google Play subscription purchases using 
the Google Play Developer API.
"""

import logging
from typing import Dict, Optional, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings

logger = logging.getLogger(__name__)


class PlayBillingService:
    """
    Service for verifying Google Play Store subscription purchases
    """
    
    # Purchase states from Google Play API
    PURCHASE_STATE_PURCHASED = 0
    PURCHASE_STATE_CANCELED = 1
    PURCHASE_STATE_PENDING = 2
    
    def __init__(self):
        """Initialize the Play billing service with credentials"""
        self.package_name = getattr(settings, 'PLAY_PACKAGE_NAME', 'com.neetbro')
        self.credentials_path = getattr(settings, 'PLAY_SERVICE_ACCOUNT_JSON', None)
        self.service = None
        
        if self.credentials_path:
            try:
                self._initialize_service()
            except Exception as e:
                logger.error(f"Failed to initialize Play billing service: {str(e)}")
    
    def _initialize_service(self):
        """Initialize Google Play Developer API client"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/androidpublisher']
            )
            
            self.service = build('androidpublisher', 'v3', credentials=credentials)
            logger.info("Play billing service initialized successfully")
        except Exception as e:
            logger.exception(f"Error initializing Play API service: {str(e)}")
            raise
    
    def verify_subscription_purchase(
        self, 
        product_id: str, 
        purchase_token: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Verify a subscription purchase with Google Play
        
        Args:
            product_id: The product/SKU ID (e.g., 'basic', 'pro')
            purchase_token: The purchase token from Play Store
            
        Returns:
            Tuple of (is_valid, purchase_data, error_message)
            - is_valid: True if purchase is valid and active
            - purchase_data: Dict containing purchase details if valid
            - error_message: Error description if invalid
        """
        if not self.service:
            error_msg = "Play billing service not initialized. Check credentials configuration."
            logger.error(error_msg)
            return False, None, error_msg
        
        try:
            logger.info(f"Verifying Play subscription: product_id={product_id}, token={purchase_token[:20]}...")
            
            # Call Google Play Developer API to verify the purchase
            result = self.service.purchases().subscriptions().get(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()
            
            logger.debug(f"Play API response: {result}")
            
            # Check purchase state
            purchase_state = result.get('paymentState', None)
            
            # paymentState: 0 = Payment pending, 1 = Payment received, 2 = Free trial, 3 = Pending deferred upgrade/downgrade
            # We accept states 1 (paid) and 2 (free trial)
            if purchase_state not in [1, 2]:
                error_msg = f"Invalid payment state: {purchase_state}"
                logger.warning(f"Purchase verification failed: {error_msg}")
                return False, None, error_msg
            
            # Check if subscription is currently valid (not expired or cancelled)
            expiry_time_millis = result.get('expiryTimeMillis')
            auto_renewing = result.get('autoRenewing', False)
            
            if not expiry_time_millis:
                error_msg = "No expiry time in purchase data"
                logger.warning(f"Purchase verification failed: {error_msg}")
                return False, None, error_msg
            
            # Convert expiry time from milliseconds to seconds
            import time
            current_time_millis = int(time.time() * 1000)
            
            if int(expiry_time_millis) < current_time_millis:
                error_msg = "Subscription has expired"
                logger.warning(f"Purchase verification failed: {error_msg}")
                return False, None, error_msg
            
            # Purchase is valid
            purchase_data = {
                'purchase_token': purchase_token,
                'product_id': product_id,
                'order_id': result.get('orderId'),
                'purchase_time_millis': result.get('startTimeMillis'),
                'expiry_time_millis': expiry_time_millis,
                'auto_renewing': auto_renewing,
                'country_code': result.get('countryCode'),
                'price_currency_code': result.get('priceCurrencyCode'),
                'payment_state': purchase_state,
            }
            
            logger.info(f"Purchase verified successfully: order_id={purchase_data['order_id']}")
            return True, purchase_data, None
            
        except HttpError as e:
            error_msg = f"Google Play API error: {e.resp.status} - {e.content}"
            logger.exception(f"Play API HttpError: {error_msg}")
            
            # Handle specific error codes
            if e.resp.status == 404:
                return False, None, "Purchase not found or invalid token"
            elif e.resp.status == 401:
                return False, None, "Authentication failed. Check service account credentials."
            elif e.resp.status == 403:
                return False, None, "Access denied. Check API permissions."
            else:
                return False, None, f"API error: {e.resp.status}"
                
        except Exception as e:
            error_msg = f"Unexpected error verifying purchase: {str(e)}"
            logger.exception(error_msg)
            return False, None, error_msg
    
    def verify_product_purchase(
        self, 
        product_id: str, 
        purchase_token: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Verify a one-time product purchase (not subscription) with Google Play
        
        Args:
            product_id: The product/SKU ID
            purchase_token: The purchase token from Play Store
            
        Returns:
            Tuple of (is_valid, purchase_data, error_message)
        """
        if not self.service:
            error_msg = "Play billing service not initialized. Check credentials configuration."
            logger.error(error_msg)
            return False, None, error_msg
        
        try:
            logger.info(f"Verifying Play product: product_id={product_id}, token={purchase_token[:20]}...")
            
            # Call Google Play Developer API for product (one-time purchase)
            result = self.service.purchases().products().get(
                packageName=self.package_name,
                productId=product_id,
                token=purchase_token
            ).execute()
            
            logger.debug(f"Play API response: {result}")
            
            # Check purchase state (0 = Purchased, 1 = Canceled, 2 = Pending)
            purchase_state = result.get('purchaseState', None)
            
            if purchase_state != self.PURCHASE_STATE_PURCHASED:
                error_msg = f"Invalid purchase state: {purchase_state}"
                logger.warning(f"Product purchase verification failed: {error_msg}")
                return False, None, error_msg
            
            # Check if already consumed/acknowledged
            consumption_state = result.get('consumptionState', 0)  # 0 = Yet to be consumed, 1 = Consumed
            acknowledgement_state = result.get('acknowledgementState', 0)  # 0 = Yet to be acknowledged, 1 = Acknowledged
            
            purchase_data = {
                'purchase_token': purchase_token,
                'product_id': product_id,
                'order_id': result.get('orderId'),
                'purchase_time_millis': result.get('purchaseTimeMillis'),
                'purchase_state': purchase_state,
                'consumption_state': consumption_state,
                'acknowledgement_state': acknowledgement_state,
                'developer_payload': result.get('developerPayload'),
            }
            
            logger.info(f"Product purchase verified successfully: order_id={purchase_data['order_id']}")
            return True, purchase_data, None
            
        except HttpError as e:
            error_msg = f"Google Play API error: {e.resp.status} - {e.content}"
            logger.exception(f"Play API HttpError: {error_msg}")
            
            if e.resp.status == 404:
                return False, None, "Purchase not found or invalid token"
            elif e.resp.status == 401:
                return False, None, "Authentication failed. Check service account credentials."
            elif e.resp.status == 403:
                return False, None, "Access denied. Check API permissions."
            else:
                return False, None, f"API error: {e.resp.status}"
                
        except Exception as e:
            error_msg = f"Unexpected error verifying purchase: {str(e)}"
            logger.exception(error_msg)
            return False, None, error_msg


# Singleton instance
_play_billing_service = None

def get_play_billing_service() -> PlayBillingService:
    """Get or create the Play billing service singleton"""
    global _play_billing_service
    if _play_billing_service is None:
        _play_billing_service = PlayBillingService()
    return _play_billing_service
