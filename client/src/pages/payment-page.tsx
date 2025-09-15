import React from 'react';
import PaymentButtons from '@/components/PaymentButtons';

const PaymentPage: React.FC = () => {
    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto">
                <PaymentButtons />
            </div>
        </div>
    );
};

export default PaymentPage;
