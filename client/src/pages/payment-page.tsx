import React from 'react';
import PaymentButtons from '@/components/PaymentButtons';

const PaymentPage: React.FC = () => {
    return (
        <div 
            className="min-h-screen"
            style={{
                backgroundImage: 'url(/payment-bg.webp)',
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
                backgroundAttachment: 'fixed'
            }}
        >
            <div className="max-w-7xl mx-auto">
                <PaymentButtons />
            </div>
        </div>
    );
};

export default PaymentPage;
