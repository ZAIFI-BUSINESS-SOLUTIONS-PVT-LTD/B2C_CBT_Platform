/**
 * TWA Android Bridge Polyfill
 * This script creates a window.Android object for TWA environments
 * where direct JavascriptInterface injection is not available
 */

(function() {
    'use strict';
    
    console.log('[TWA Bridge] Initializing Android bridge polyfill');
    
    // Create Android bridge object if it doesn't exist
    if (typeof window.Android === 'undefined') {
        console.log('[TWA Bridge] Creating window.Android polyfill');
        
        window.Android = {
            purchase: function(productId) {
                console.log('[TWA Bridge] purchase() called for:', productId);
                
                // Store the request in localStorage for the native app to read
                localStorage.setItem('twa_purchase_request', JSON.stringify({
                    productId: productId,
                    timestamp: Date.now()
                }));
                
                // Trigger a custom event that the native app can listen for
                window.dispatchEvent(new CustomEvent('twa-purchase-request', {
                    detail: { productId: productId }
                }));
                
                // Try to communicate via URL change (fallback)
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.set('twa_action', 'purchase');
                currentUrl.searchParams.set('product_id', productId);
                window.history.pushState({}, '', currentUrl.toString());
                
                return true;
            },
            
            getPurchaseResult: function() {
                console.log('[TWA Bridge] getPurchaseResult() called');
                
                // Check localStorage for purchase result
                const result = localStorage.getItem('twa_purchase_result');
                if (result) {
                    localStorage.removeItem('twa_purchase_result');
                    return result;
                }
                
                // Check URL parameters
                const params = new URLSearchParams(window.location.search);
                const purchaseToken = params.get('purchase_token');
                const productId = params.get('product_id');
                
                if (purchaseToken && productId) {
                    return JSON.stringify({
                        purchaseToken: purchaseToken,
                        productId: productId
                    });
                }
                
                return null;
            },
            
            hasPendingPurchase: function() {
                console.log('[TWA Bridge] hasPendingPurchase() called');
                
                // Check localStorage
                const result = localStorage.getItem('twa_purchase_result');
                if (result) {
                    return true;
                }
                
                // Check URL parameters
                const params = new URLSearchParams(window.location.search);
                return params.has('purchase_token') && params.has('product_id');
            }
        };
        
        console.log('[TWA Bridge] window.Android polyfill created successfully');
        
        // Dispatch ready event
        window.dispatchEvent(new Event('twa-android-bridge-ready'));
    } else {
        console.log('[TWA Bridge] Native window.Android already exists');
    }
})();
