import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { createOrder, verifyPayment, getSubscriptionStatus } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle, Clock, Star, Crown, ChevronLeft } from 'lucide-react';
import { useLocation } from 'wouter';
import { isTWA, verifyPlayPurchase } from '@/utils/twa';

// Extend Window interface for Razorpay
declare global {
  interface Window {
    Razorpay: any;
  }
}

interface SubscriptionStatus {
  // support both snake_case (backend Django) and camelCase (API normalization)
  subscription_plan?: string | null;
  subscriptionPlan?: string | null;
  subscription_expires_at?: string | null;
  subscriptionExpiresAt?: string | null;
  is_active?: boolean;
  isActive?: boolean;
  available_plans?: {
    basic: number;
    pro: number;
  };
  availablePlans?: {
    basic: number;
    pro: number;
  };
}

const PaymentButtons: React.FC = () => {
  const [loading, setLoading] = useState<string | null>(null);
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const { toast } = useToast();
  const { student } = useAuth();
  const [, navigate] = useLocation();

  useEffect(() => {
    loadSubscriptionStatus();
  }, []);

  // Development-only debug: print out sources used for current plan
  useEffect(() => {
    console.debug('[DEBUG] subscriptionStatus (API):', subscriptionStatus);
  }, [subscriptionStatus]);

  const loadSubscriptionStatus = async () => {
    try {
      const status = await getSubscriptionStatus();
      setSubscriptionStatus(status);
    } catch (error) {
      console.error('Failed to load subscription status:', error);
      toast({
        title: "Error",
        description: "Failed to load subscription status",
        variant: "destructive"
      });
    } finally {
      setLoadingStatus(false);
    }
  };

  // Helper: format expiry date into a friendly string (date + days left)
  const formatExpiry = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'Never';
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const diffMs = d.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays > 0) {
      return `${d.toLocaleDateString()} (${diffDays} day${diffDays > 1 ? 's' : ''} left)`;
    }
    return `${d.toLocaleDateString()} (expired)`;
  };

  // Render a small card that shows the current plan and expiry (active or not)
  const CurrentPlanCard: React.FC = () => {
    // Prefer subscriptionStatus from API, but fall back to `student` from AuthContext
    // Support both snake_case and camelCase field names from API/auth
    const plan = (
      (subscriptionStatus as any)?.subscription_plan ??
      (subscriptionStatus as any)?.subscriptionPlan ??
      (student as any)?.subscription_plan ??
      (student as any)?.subscriptionPlan ??
      null
    );
    const expiresRaw = (
      (subscriptionStatus as any)?.subscription_expires_at ??
      (subscriptionStatus as any)?.subscriptionExpiresAt ??
      (student as any)?.subscription_expires_at ??
      (student as any)?.subscriptionExpiresAt ??
      null
    );
    const expires = formatExpiry(expiresRaw);

    // If we have neither API data nor auth profile, show a simple placeholder prompting login
    if (!plan && !expiresRaw) {
      return (
        <div className="w-full mb-4 px-4">
          <Card className="w-full">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-500">Current plan</p>
                  <p className="text-lg font-semibold">None</p>
                  <p className="text-sm text-gray-600">Expires: Never</p>
                </div>
                <div className="ml-4">
                  <Badge variant="outline" className="text-xs">NO PLAN</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    // Determine active state: prefer API `is_active`, otherwise derive from expiresRaw
    const isActive = (
      (subscriptionStatus as any)?.is_active ??
      (subscriptionStatus as any)?.isActive ??
      (!!expiresRaw && new Date(expiresRaw) > new Date())
    );

    return (
      <div className="w-full mb-4 px-4">
        <Card className="w-full">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm text-gray-500">Current plan</p>
                <p className="text-lg font-semibold">{plan ? plan.toUpperCase() : 'None'}</p>
                <p className="text-sm text-gray-600">Expires: {expires}</p>
              </div>
              <div className="ml-4">
                {isActive ? (
                  <Badge className="bg-green-600 text-xs">ACTIVE</Badge>
                ) : plan ? (
                  <Badge variant="secondary" className="text-xs">INACTIVE</Badge>
                ) : (
                  <Badge variant="outline" className="text-xs">NO PLAN</Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const loadRazorpayScript = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handlePayment = async (plan: 'basic' | 'premium' | 'pro') => {
    setLoading(plan);

    try {
      // Check if running in TWA (Android app)
      if (isTWA()) {
        // Purchases in TWA are launched via the Payment Request API with
        // 'https://play.google.com/billing' as the payment method.
        // The Digital Goods API (getDigitalGoodsService) is QUERY-only and has no purchase().
        // total.amount.value must be "0" (Play billing ignores web price; uses Play Console price).
        try {
          // The Digital Goods API and PaymentRequest expect only the subscription product ID.
          // Each plan maps to its own Play Console subscription product.
          const planSKUMap: Record<string, string> = {
            basic:   'neetbro_subscription',
            premium: 'neetbro_premium',
            pro:     'neetbro_pro',
          };
          const playSKU = planSKUMap[plan] ?? 'neetbro_subscription';
          console.log(`[TWA] Initiating Play purchase via PaymentRequest for SKU: ${playSKU}`);

          const request = new PaymentRequest(
            [
              {
                supportedMethods: 'https://play.google.com/billing',
                data: { sku: playSKU },
              },
            ],
            {
              total: {
                label: 'NEET BRO Subscription',
                amount: { currency: 'INR', value: '0' },
              },
            }
          );

          const canPay = await request.canMakePayment();
          console.log('[TWA] canMakePayment:', canPay);

          if (!canPay) {
            // canMakePayment false = Play billing not wired up in this build/device.
            // Likely causes: app not installed from Play Store, billing library missing,
            // or running outside a TWA context.
            throw new Error(
              'Google Play Billing is not available. ' +
              'Make sure you installed the app from the Play Store.'
            );
          }

          // Show the Play purchase sheet
          const response = await request.show();

          // Robustly extract purchaseToken from response.details.
          // Different Android/WebView builds may:
          //   - Return details as a JSON string instead of a plain object
          //   - Use snake_case keys (purchase_token)
          //   - Return null / undefined details
          let details: Record<string, any> = {};
          try {
            const raw = response.details;
            if (raw === null || raw === undefined) {
              console.warn('[TWA] response.details is null/undefined');
            } else if (typeof raw === 'string') {
              details = JSON.parse(raw);
            } else if (typeof raw === 'object') {
              details = raw as Record<string, any>;
            }
          } catch (parseErr) {
            console.error('[TWA] Could not parse response.details:', response.details, parseErr);
          }

          console.log('[TWA] response.details keys:', Object.keys(details));
          console.log('[TWA] response.details (full):', JSON.stringify(details));

          // Play Billing may key the token differently across Android versions
          const purchaseToken: string =
            details.purchaseToken ||
            details.purchase_token ||
            details.token;

          if (!purchaseToken) {
            // Signal failure to Play so the purchase isn't left in a pending state
            await response.complete('fail');
            console.error('[TWA] No purchaseToken found. Keys present:', Object.keys(details));
            throw new Error(
              `No purchase token returned by Google Play. ` +
              `Keys in response: [${Object.keys(details).join(', ') || 'none'}]. ` +
              `Full: ${JSON.stringify(details)}`
            );
          }

          // Token acquired — close the Play UI with success
          await response.complete('success');

          console.log('[TWA] Purchase token received:', purchaseToken.substring(0, 20) + '...');

          // Token stored as 'accessToken' in localStorage; also check 'access' cookie fallback
          // set by auth.ts for TWA environments where localStorage may not persist.
          const accessToken =
            localStorage.getItem('accessToken') ||
            document.cookie
              .split('; ')
              .find(row => row.startsWith('access='))
              ?.split('=')[1];
          if (!accessToken) {
            toast({
              title: 'Authentication Error',
              description: 'Please log in again to complete the purchase.',
              variant: 'destructive',
            });
            setLoading(null);
            return;
          }

          // Verify the purchase token with the Django backend
          const result = await verifyPlayPurchase(purchaseToken, playSKU, accessToken);
          console.log('[TWA] Play purchase verified:', result);

          toast({
            title: 'Success!',
            description: `Successfully subscribed to ${result.plan} plan via Google Play!`,
            variant: 'default',
          });

          await loadSubscriptionStatus();
        } catch (err: any) {
          console.error('[TWA] Play billing error:', err);

          // AbortError = user cancelled the purchase sheet — don't show an error toast
          if (err?.name === 'AbortError' || err?.code === 20) {
            console.log('[TWA] Purchase cancelled by user.');
          } else {
            // RESULT_CANCELED from Play Store usually means the SKU does not exist
            // in Play Console, or the tester account is not a licensed tester.
            const isResultCanceled =
              typeof err?.message === 'string' && err.message.includes('RESULT_CANCELED');

            toast({
              title: 'Payment Failed',
              description: isResultCanceled
                ? 'Purchase cancelled by Google Play. Check that the subscription product exists in Play Console and your test account is a licensed tester.'
                : err?.message || 'Google Play purchase failed. Please try again.',
              variant: 'destructive',
            });
          }
        }

        setLoading(null);
        return;
      }

      // Web flow: Use Razorpay
      // Load Razorpay script
      const isRazorpayLoaded = await loadRazorpayScript();
      if (!isRazorpayLoaded) {
        toast({
          title: "Error",
          description: "Failed to load payment gateway",
          variant: "destructive"
        });
        return;
      }

      // Create order on backend
      const orderData = await createOrder(plan);
      console.debug('[DEBUG] createOrder response:', orderData);

      const options = {
        // Razorpay checkout expects `key` - backend returns `key_id`. Accept either.
        key: orderData.key || orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'NEET Ninja',
        description: `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan Subscription`,
        order_id: orderData.order_id,
        handler: async function (response: any) {
          try {
            // Verify payment on backend
            const verifyPayload = {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              local_order_id: orderData.local_order_id
            };

            const result = await verifyPayment(verifyPayload);
            toast({
              title: "Success!",
              description: `Successfully subscribed to ${plan} plan!`,
              variant: "default"
            });

            // Reload subscription status
            await loadSubscriptionStatus();
          } catch (error) {
            console.error('Payment verification failed:', error);
            toast({
              title: "Payment Failed",
              description: "Payment verification failed. Please contact support.",
              variant: "destructive"
            });
          }
        },
        prefill: {
          email: '',
          contact: ''
        },
        notes: {
          plan: plan
        },
        theme: {
          color: '#6366f1'
        },
        modal: {
          ondismiss: function () {
            toast({
              title: "Payment Cancelled",
              description: "Payment was cancelled",
              variant: "default"
            });
          }
        }
      };

      console.debug('[DEBUG] Razorpay options before init:', options);
      if (!options.key) {
        console.error('[ERROR] Razorpay options missing key:', options);
        throw new Error('Missing payment gateway key');
      }

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (error) {
      console.error('Failed to initiate payment:', error);
      toast({
        title: "Error",
        description: "Failed to initiate payment",
        variant: "destructive"
      });
    } finally {
      setLoading(null);
    }
  };

  if (loadingStatus) {
    return (
      <div className="min-h-screen bg-white">
        {/* Header */}
        <div className="sticky top-0 bg-white z-50 border-b border-gray-200 shadow-sm">
          <div className="w-full px-4 py-3 inline-flex items-center gap-3">
            <Button variant="secondary" size="icon" className="size-8" onClick={() => navigate('/')}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-lg font-bold text-gray-900">Payment</h1>
          </div>
        </div>

        <div className="flex justify-center items-center py-12 pt-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (subscriptionStatus?.is_active) {
    return (
      <div className="min-h-screen bg-white">
        {/* Header */}
        <div className="sticky top-0 bg-white z-50 border-b border-gray-200 shadow-sm">
          <div className="w-full px-4 py-3 inline-flex items-center gap-3">
            <Button variant="secondary" size="icon" className="size-8" onClick={() => navigate('/')}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-lg font-bold text-gray-900">Payment</h1>
          </div>
        </div>

        <div className="space-y-6 py-6 pt-20">
          <CurrentPlanCard />
          <div className="px-4">
            <Card className="w-full">
              <CardHeader className="text-center pb-4">
                <div className="flex justify-center mb-3">
                  <CheckCircle className="h-12 w-12 text-green-500" />
                </div>
                <CardTitle className="text-xl text-green-600">Active Subscription</CardTitle>
                <CardDescription className="text-sm">
                  You have an active {(
                    (subscriptionStatus as any)?.subscription_plan ??
                    (subscriptionStatus as any)?.subscriptionPlan ??
                    subscriptionStatus?.subscription_plan ??
                    subscriptionStatus?.subscriptionPlan ??
                    ''
                  )} plan
                </CardDescription>
              </CardHeader>
              <CardContent className="text-center pt-0">
                <Badge variant="secondary" className="mb-4 text-xs">
                  <Crown className="h-4 w-4 mr-1" />
                  {(
                    (subscriptionStatus as any)?.subscription_plan ??
                    (subscriptionStatus as any)?.subscriptionPlan ??
                    subscriptionStatus?.subscription_plan ??
                    subscriptionStatus?.subscriptionPlan ??
                    ''
                  )?.toUpperCase()} PLAN
                </Badge>
                <p className="text-sm text-gray-600">
                  <Clock className="h-4 w-4 inline mr-1" />
                  Expires: {formatExpiry((subscriptionStatus as any)?.subscription_expires_at ?? (subscriptionStatus as any)?.subscriptionExpiresAt ?? subscriptionStatus?.subscription_expires_at ?? subscriptionStatus?.subscriptionExpiresAt)}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="sticky top-0 bg-white z-50 border-b border-gray-200 shadow-sm">
        <div className="w-full px-4 py-3 inline-flex items-center gap-3">
          <Button variant="secondary" size="icon" className="size-8" onClick={() => navigate('/')}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-lg font-bold text-gray-900">Payment</h1>
        </div>
      </div>

      <div className="py-6">
        <CurrentPlanCard />
        <div className="text-center mb-6 px-4">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Choose Your Plan</h2>
          <p className="text-sm text-gray-600">Unlock premium features and boost your NEET preparation</p>
        </div>

        <div className="space-y-4 px-4">
          {/* Basic Plan */}
          <Card className="w-full border-2 hover:border-blue-300 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg text-blue-600">Basic Plan</CardTitle>
                  <CardDescription className="text-sm">Perfect for getting started</CardDescription>
                </div>
                <Badge variant="outline" className="text-xs ml-2">Starter</Badge>
              </div>
              <div className="mt-3">
                <span className="text-2xl font-bold">₹720</span>
                <span className="text-sm text-gray-500">/3 months</span>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="space-y-2 mb-4">
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Unlimited practice tests
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Performance analytics
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Basic study insights
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Chapter-wise tests
                </li>
              </ul>
              <Button
                className="w-full h-11 text-sm font-medium"
                onClick={() => handlePayment('basic')}
                disabled={loading !== null}
              >
                {loading === 'basic' ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Processing...
                  </>
                ) : (
                  'Subscribe to Basic'
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Premium Plan */}
          <Card className="w-full border-2 border-orange-300 hover:border-orange-400 transition-colors relative">
            <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
              <Badge className="bg-orange-600 hover:bg-orange-700 text-xs px-2 py-1">
                <Star className="h-3 w-3 mr-1" />
                Popular
              </Badge>
            </div>
            <CardHeader className="pb-3 pt-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg text-orange-600">Premium Plan</CardTitle>
                  <CardDescription className="text-sm">Best value for serious students</CardDescription>
                </div>
                <Star className="h-5 w-5 text-orange-600 flex-shrink-0" />
              </div>
              <div className="mt-3">
                <span className="text-2xl font-bold">₹7,200</span>
                <span className="text-sm text-gray-500">/3 months</span>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="space-y-2 mb-4">
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Everything in Basic Plan
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Advanced performance analytics
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  AI-powered study insights
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Personalized study plans
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  AI chatbot tutor
                </li>
              </ul>
              <Button
                className="w-full h-11 text-sm font-medium bg-orange-600 hover:bg-orange-700"
                onClick={() => handlePayment('premium')}
                disabled={loading !== null}
              >
                {loading === 'premium' ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Processing...
                  </>
                ) : (
                  'Subscribe to Premium'
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Pro Plan */}
          <Card className="w-full border-2 border-purple-300 hover:border-purple-400 transition-colors relative">
            <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
              <Badge className="bg-purple-600 hover:bg-purple-700 text-xs px-2 py-1">
                <Crown className="h-3 w-3 mr-1" />
                Ultimate
              </Badge>
            </div>
            <CardHeader className="pb-3 pt-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg text-purple-600">Pro Plan</CardTitle>
                  <CardDescription className="text-sm">Complete NEET preparation suite</CardDescription>
                </div>
                <Crown className="h-5 w-5 text-purple-600 flex-shrink-0" />
              </div>
              <div className="mt-3">
                <span className="text-2xl font-bold">₹17,000</span>
                <span className="text-sm text-gray-500">/3 months</span>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="space-y-2 mb-4">
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Everything in Premium Plan
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Advanced AI chatbot tutor
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Priority support (24/7)
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Exclusive mock test series
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  One-on-one mentorship sessions
                </li>
                <li className="flex items-center text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  Doubt resolution within 1 hour
                </li>
              </ul>
              <Button
                className="w-full h-11 text-sm font-medium bg-purple-600 hover:bg-purple-700"
                onClick={() => handlePayment('pro')}
                disabled={loading !== null}
              >
                {loading === 'pro' ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Processing...
                  </>
                ) : (
                  'Subscribe to Pro'
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="text-center text-xs text-gray-500 mt-6 px-4">
          <p className="mb-1">Secure payments powered by Razorpay & Google Play</p>
          <p>All plans are for 3-month subscription period with auto-renewal</p>
        </div>
      </div>
    </div>
  );
};

export default PaymentButtons;
