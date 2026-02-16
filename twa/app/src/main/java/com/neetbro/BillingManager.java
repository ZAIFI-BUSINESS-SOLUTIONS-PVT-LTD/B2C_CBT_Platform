package com.neetbro;

import android.app.Activity;
import com.android.billingclient.api.*;

import java.util.Collections;

public class BillingManager implements PurchasesUpdatedListener {

    private BillingClient billingClient;
    private Activity activity;

    public interface PurchaseListener {
        void onPurchaseSuccess(String purchaseToken, String productId);
    }

    private PurchaseListener listener;

    public BillingManager(Activity activity, PurchaseListener listener) {
        this.activity = activity;
        this.listener = listener;

        billingClient = BillingClient.newBuilder(activity)
                .setListener(this)
                .enablePendingPurchases()
                .build();

        billingClient.startConnection(new BillingClientStateListener() {
            @Override
            public void onBillingSetupFinished(BillingResult billingResult) { }

            @Override
            public void onBillingServiceDisconnected() { }
        });
    }

    public void startPurchase(String productId) {
        QueryProductDetailsParams params =
                QueryProductDetailsParams.newBuilder()
                        .setProductList(Collections.singletonList(
                                QueryProductDetailsParams.Product.newBuilder()
                                        .setProductId(productId)
                                        .setProductType(BillingClient.ProductType.SUBS)
                                        .build()))
                        .build();

        billingClient.queryProductDetailsAsync(params, (result, productDetailsList) -> {
            if (productDetailsList.isEmpty()) return;

            ProductDetails productDetails = productDetailsList.get(0);

            BillingFlowParams.ProductDetailsParams pdp =
                    BillingFlowParams.ProductDetailsParams.newBuilder()
                            .setProductDetails(productDetails)
                            .setOfferToken(productDetails.getSubscriptionOfferDetails().get(0).getOfferToken())
                            .build();

            BillingFlowParams flowParams =
                    BillingFlowParams.newBuilder()
                            .setProductDetailsParamsList(Collections.singletonList(pdp))
                            .build();

            billingClient.launchBillingFlow(activity, flowParams);
        });
    }

    @Override
    public void onPurchasesUpdated(BillingResult billingResult,
                                   java.util.List<Purchase> purchases) {

        if (purchases == null) return;

        for (Purchase purchase : purchases) {
            if (purchase.getPurchaseState() == Purchase.PurchaseState.PURCHASED) {
                listener.onPurchaseSuccess(
                        purchase.getPurchaseToken(),
                        purchase.getProducts().get(0)
                );
            }
        }
    }
}
