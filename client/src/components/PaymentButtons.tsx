import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { createOrder, verifyPayment, getSubscriptionStatus } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle, Clock, Star, Crown } from 'lucide-react';
 
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
        <div className="max-w-4xl mx-auto mb-6">
          <Card className="w-full">
            <CardContent className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Current plan</p>
                <p className="text-lg font-semibold">None</p>
                <p className="text-sm text-gray-600">Expires: Never</p>
              </div>
              <div>
                <Badge variant="outline">NO PLAN</Badge>
              </div>
            </CardContent>
          </Card>
          {/* Dev debug panel */}
          <div className="mt-2 text-xs text-gray-500">
            <details>
              <summary>Debug: plan sources</summary>
              <pre className="p-2 bg-gray-100 rounded">API: {JSON.stringify(subscriptionStatus, null, 2)}</pre>
              <pre className="p-2 bg-gray-100 rounded mt-2">Auth student: {JSON.stringify(student, null, 2)}</pre>
            </details>
          </div>
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
      <div className="max-w-4xl mx-auto mb-6">
        <Card className="w-full">
          <CardContent className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Current plan</p>
              <p className="text-lg font-semibold">{plan ? plan.toUpperCase() : 'None'}</p>
              <p className="text-sm text-gray-600">Expires: {expires}</p>
            </div>
            <div>
              {isActive ? (
                <Badge className="bg-green-600">ACTIVE</Badge>
              ) : plan ? (
                <Badge variant="secondary">INACTIVE</Badge>
              ) : (
                <Badge variant="outline">NO PLAN</Badge>
              )}
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
 
  const handlePayment = async (plan: 'basic' | 'pro') => {
    setLoading(plan);
 
    try {
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
          ondismiss: function() {
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
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }
 
  if (subscriptionStatus?.is_active) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <CurrentPlanCard />
        <Card className="max-w-md mx-auto">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-2">
              <CheckCircle className="h-12 w-12 text-green-500" />
            </div>
            <CardTitle className="text-green-600">Active Subscription</CardTitle>
            <CardDescription>
              You have an active {(
                (subscriptionStatus as any)?.subscription_plan ??
                (subscriptionStatus as any)?.subscriptionPlan ??
                subscriptionStatus?.subscription_plan ??
                subscriptionStatus?.subscriptionPlan ??
                ''
              )} plan
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <Badge variant="secondary" className="mb-4">
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
    );
  }
 
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <CurrentPlanCard />
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Choose Your Plan</h2>
        <p className="text-gray-600">Unlock premium features and boost your NEET preparation</p>
      </div>
 
      <div className="grid md:grid-cols-2 gap-6">
        {/* Basic Plan */}
        <Card className="relative border-2 hover:border-blue-300 transition-colors">
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-xl text-blue-600">Basic Plan</CardTitle>
                <CardDescription>Perfect for regular practice</CardDescription>
              </div>
              <Badge variant="outline">Popular</Badge>
            </div>
            <div className="mt-4">
              <span className="text-3xl font-bold">₹1,500</span>
              <span className="text-gray-500">/month</span>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 mb-6">
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Unlimited practice tests
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Detailed performance analytics
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                AI-powered study insights
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Chapter-wise tests
              </li>
            </ul>
            <Button
              className="w-full"
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
 
        {/* Pro Plan */}
        <Card className="relative border-2 border-purple-300 hover:border-purple-400 transition-colors">
          <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
            <Badge className="bg-purple-600 hover:bg-purple-700">
              <Star className="h-3 w-3 mr-1" />
              Recommended
            </Badge>
          </div>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-xl text-purple-600">Pro Plan</CardTitle>
                <CardDescription>Complete NEET preparation suite</CardDescription>
              </div>
              <Crown className="h-6 w-6 text-purple-600" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-bold">₹2,500</span>
              <span className="text-gray-500">/month</span>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 mb-6">
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Everything in Basic Plan
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Official NEET papers access
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Advanced AI chatbot tutor
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Priority support
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Detailed explanations
              </li>
            </ul>
            <Button
              className="w-full bg-purple-600 hover:bg-purple-700"
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
 
      <div className="text-center text-sm text-gray-500 mt-6">
        <p>Secure payments powered by Razorpay</p>
        <p>All plans include 30-day subscription period</p>
      </div>
    </div>
  );
};
 
export default PaymentButtons;
 