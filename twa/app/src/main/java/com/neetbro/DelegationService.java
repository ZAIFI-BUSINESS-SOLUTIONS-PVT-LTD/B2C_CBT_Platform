package com.neetbro;

import android.os.Bundle;
import android.util.Log;

public class DelegationService extends
        com.google.androidbrowserhelper.trusted.DelegationService {
    
    private static final String TAG = "DelegationService";
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "DelegationService created");
    }
}


