package com.neetbro;

import android.app.Activity;
import androidx.annotation.NonNull;
import com.android.billingclient.api.*;

import java.util.Collections;
import java.util.List;

public class BillingManager implements PurchasesUpdatedListener {

    private final BillingClient billingClient;
    private final Activity activity;

    public interface PurchaseListener {
        void onPurchaseSuccess(String purchaseToken, String productId);
    }

    private final PurchaseListener listener;

    public BillingManager(Activity activity, PurchaseListener listener) {
        this.activity = activity;
        this.listener = listener;

        billingClient = BillingClient.newBuilder(activity)
                .setListener(this)
                .enablePendingPurchases(
                    PendingPurchasesParams.newBuilder()
                        .enableOneTimeProducts()
                        .build()
                )
                .build();

        billingClient.startConnection(new BillingClientStateListener() {
            @Override
            public void onBillingSetupFinished(@NonNull BillingResult billingResult) { }

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

        billingClient.queryProductDetailsAsync(params, new ProductDetailsResponseListener() {
            @Override
            public void onProductDetailsResponse(@NonNull BillingResult billingResult, 
                                                @NonNull QueryProductDetailsResult queryProductDetailsResult) {
                List<ProductDetails> productDetailsList = queryProductDetailsResult.getProductDetailsList();
                
                if (productDetailsList == null || productDetailsList.isEmpty()) return;

                ProductDetails productDetails = productDetailsList.get(0);
                
                if (productDetails.getSubscriptionOfferDetails() == null || 
                    productDetails.getSubscriptionOfferDetails().isEmpty()) return;

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
            }
        });
    }

    @Override
    public void onPurchasesUpdated(@NonNull BillingResult billingResult,
                                   List<Purchase> purchases) {

        if (purchases == null) return;

        for (Purchase purchase : purchases) {
            if (purchase.getPurchaseState() == Purchase.PurchaseState.PURCHASED) {
                List<String> products = purchase.getProducts();
                if (!products.isEmpty()) {
                    listener.onPurchaseSuccess(
                            purchase.getPurchaseToken(),
                            products.get(0)
                    );
                }
            }
        }
    }
}
