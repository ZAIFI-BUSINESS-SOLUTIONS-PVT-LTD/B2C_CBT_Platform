import React, { Suspense, useEffect, useState } from 'react';

// Lazy-load mobile and desktop chatbot components to keep bundles small
const Mobilechatbot = React.lazy(() => import('../mobile/chatbot'));
const Desktopchatbot = React.lazy(() => import('../desktop/chatbot-desktop'));

/**
 * Responsive chatbot wrapper
 * - Renders Desktopchatbot when viewport width >= 1024px (matches Tailwind's lg breakpoint)
 * - Renders Mobilechatbot otherwise
 */
export default function chatbotResponsive(): JSX.Element {
    const [isDesktop, setIsDesktop] = useState<boolean>(() => {
        if (typeof window === 'undefined') return false;
        return window.matchMedia('(min-width: 1024px)').matches;
    });

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const mq = window.matchMedia('(min-width: 1024px)');
        const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
        // Older browsers use addListener
        if (mq.addEventListener) mq.addEventListener('change', handler);
        else mq.addListener(handler as any);
        return () => {
            if (mq.removeEventListener) mq.removeEventListener('change', handler);
            else mq.removeListener(handler as any);
        };
    }, []);

    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            {isDesktop ? <Desktopchatbot /> : <Mobilechatbot />}
        </Suspense>
    );
}
