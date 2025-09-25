import React, { Suspense, useEffect, useState } from 'react';

// Lazy-load mobile and desktop dashboard components to keep bundles small
const Mobiledashboard = React.lazy(() => import('../dashboard'));
const Desktopdashboard = React.lazy(() => import('../desktop/dashboard-desktop'));

/**
 * Responsive dashboard wrapper
 * - Renders Desktopdashboard when viewport width >= 1024px (matches Tailwind's lg breakpoint)
 * - Renders Mobiledashboard otherwise
 */
export default function dashboardResponsive(): JSX.Element {
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
            {isDesktop ? <Desktopdashboard /> : <Mobiledashboard />}
        </Suspense>
    );
}
