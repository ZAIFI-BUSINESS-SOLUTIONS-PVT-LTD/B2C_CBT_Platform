/*
 * Copyright 2020 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.neetbro;

import android.content.pm.ActivityInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.util.Log;
import com.google.androidbrowserhelper.trusted.TwaLauncher;


public class LauncherActivity
        extends com.google.androidbrowserhelper.trusted.LauncherActivity {

    private static final String TAG = "LauncherActivity";
    private BillingManager billingManager;
    private String pendingPurchaseToken;
    private String pendingProductId;
    private static LauncherActivity instance;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        instance = this;

        if (Build.VERSION.SDK_INT > Build.VERSION_CODES.O) {
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        } else {
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
        }

        // Initialize BillingManager
        billingManager = new BillingManager(this, (token, productId) -> {
            // Store purchase info to be retrieved by JavaScript
            pendingPurchaseToken = token;
            pendingProductId = productId;
            Log.d(TAG, "Purchase completed: " + productId);
            
            // Trigger a JavaScript event via page reload with purchase data in URL
            // This ensures React receives the purchase info
            runOnUiThread(() -> {
                // The web app will call getPurchaseResult() via JavaScript interface
                // to retrieve the purchase data
            });
        });
    }
    
    public static LauncherActivity getInstance() {
        return instance;
    }

    @Override
    protected Uri getLaunchingUrl() {
        Uri uri = super.getLaunchingUrl();
        return uri;
    }

    // JavaScript interface exposed to React app
    @JavascriptInterface
    public void purchase(String productId) {
        billingManager.startPurchase(productId);
    }
    
    // JavaScript interface to retrieve purchase result
    // React calls this after purchase to get the token and productId
    @JavascriptInterface
    public String getPurchaseResult() {
        if (pendingPurchaseToken != null && pendingProductId != null) {
            String result = "{\"purchaseToken\":\"" + pendingPurchaseToken + 
                          "\",\"productId\":\"" + pendingProductId + "\"}";
            // Clear after retrieval
            pendingPurchaseToken = null;
            pendingProductId = null;
            return result;
        }
        return null;
    }
    
    // JavaScript interface to check if there's a pending purchase
    @JavascriptInterface
    public boolean hasPendingPurchase() {
        return pendingPurchaseToken != null && pendingProductId != null;
    }
}
