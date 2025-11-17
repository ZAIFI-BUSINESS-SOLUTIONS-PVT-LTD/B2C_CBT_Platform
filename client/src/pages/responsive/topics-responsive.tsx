import React, { Suspense, useEffect, useState } from 'react';

// Lazy-load mobile and desktop topics components to keep bundles small
const Mobiletopics = React.lazy(() => import('../mobile/topics'));
const Desktoptopics = React.lazy(() => import('../desktop/topics-desktop'));

/**
 * Responsive topics wrapper
 * - Renders Desktoptopics when viewport width >= 1024px (matches Tailwind's lg breakpoint)
 * - Renders Mobiletopics otherwise
 */
export default function topicsResponsive(): JSX.Element {
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
            {isDesktop ? <Desktoptopics /> : <Mobiletopics />}
        </Suspense>
    );
}
