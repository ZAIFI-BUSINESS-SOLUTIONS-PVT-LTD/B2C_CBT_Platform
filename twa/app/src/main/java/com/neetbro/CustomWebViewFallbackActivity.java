package com.neetbro;

import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;
import android.util.Log;

/**
 * Custom WebView Fallback Activity with JavaScript interface injection
 * This is used when Chrome Custom Tabs is not available OR when fallbackType is set to 'webview'
 */
public class CustomWebViewFallbackActivity extends com.google.androidbrowserhelper.trusted.WebViewFallbackActivity {
    
    private static final String TAG = "CustomWebViewFallback";
    private LauncherActivity launcherActivity;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        launcherActivity = LauncherActivity.getInstance();
        Log.d(TAG, "CustomWebViewFallbackActivity created");
        
        // Setup WebView after creation
        setupWebViewAfterCreate();
    }
    
    private void setupWebViewAfterCreate() {
        // Post a runnable to ensure WebView is fully initialized
        findViewById(android.R.id.content).post(() -> {
            WebView webView = findWebViewInHierarchy();
            if (webView != null) {
                setupWebView(webView);
                
                // Set custom WebViewClient
                webView.setWebViewClient(new WebViewClient() {
                    @Override
                    public void onPageFinished(WebView view, String url) {
                        super.onPageFinished(view, url);
                        Log.d(TAG, "Page loaded: " + url);
                        injectAndroidBridge(view);
                    }
                });
            }
        });
    }
    
    @Override
    protected void onStart() {
        super.onStart();
        // Try to inject the bridge when activity starts
        WebView webView = findWebViewInHierarchy();
        if (webView != null) {
            setupWebView(webView);
        }
    }
    
    private WebView findWebViewInHierarchy() {
        // Try to find the WebView in the activity's view hierarchy
        try {
            android.view.View rootView = findViewById(android.R.id.content).getRootView();
            if (rootView instanceof WebView) {
                return (WebView) rootView;
            }
            // Try to find by tag
            android.view.View taggedView = rootView.findViewWithTag("customWebView");
            if (taggedView instanceof WebView) {
                return (WebView) taggedView;
            }
        } catch (Exception e) {
            Log.w(TAG, "Could not find WebView", e);
        }
        return null;
    }
    
    private void setupWebView(WebView webView) {
        if (webView == null) {
            Log.w(TAG, "WebView is null, cannot setup");
            return;
        }
        
        try {
            // Enable JavaScript
            WebSettings settings = webView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setAllowFileAccess(false);
            settings.setAllowContentAccess(false);
            
            // Inject Android JavaScript interface
            webView.addJavascriptInterface(new AndroidBridge(), "Android");
            Log.d(TAG, "Android JavaScript interface injected successfully");
        } catch (Exception e) {
            Log.e(TAG, "Error setting up WebView", e);
        }
    }
    
    private void injectAndroidBridge(WebView webView) {
        if (webView == null) {
            return;
        }
        
        // Inject Android bridge if not already present
        webView.evaluateJavascript(
            "(function() {" +
            "  if (typeof window.Android === 'undefined') {" +
            "    console.log('[TWA] Android bridge detected via native injection');" +
            "  } else {" +
            "    console.log('[TWA] Android bridge already exists');" +
            "  }" +
            "  window.dispatchEvent(new Event('twa-bridge-ready'));" +
            "})();",
            null
        );
    }
    
    /**
     * JavaScript interface bridge
     */
    private class AndroidBridge {
        
        @JavascriptInterface
        public void purchase(String productId) {
            Log.d(TAG, "purchase() called for productId: " + productId);
            if (launcherActivity != null) {
                launcherActivity.runOnUiThread(() -> launcherActivity.purchase(productId));
            } else {
                Log.e(TAG, "LauncherActivity instance is null");
            }
        }
        
        @JavascriptInterface
        public String getPurchaseResult() {
            Log.d(TAG, "getPurchaseResult() called");
            if (launcherActivity != null) {
                return launcherActivity.getPurchaseResult();
            }
            return null;
        }
        
        @JavascriptInterface
        public boolean hasPendingPurchase() {
            Log.d(TAG, "hasPendingPurchase() called");
            if (launcherActivity != null) {
                return launcherActivity.hasPendingPurchase();
            }
            return false;
        }
    }
}
