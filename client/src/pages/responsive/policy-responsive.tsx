import React, { Suspense, useEffect, useState } from 'react';

const MobilePolicy = React.lazy(() => import('../mobile/policy'));
const DesktopPolicy = React.lazy(() => import('../desktop/policy-desktop'));

export default function PolicyResponsive(): JSX.Element {
    const [isDesktop, setIsDesktop] = useState<boolean>(() => {
        if (typeof window === 'undefined') return false;
        return window.matchMedia('(min-width: 1024px)').matches;
    });

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const mq = window.matchMedia('(min-width: 1024px)');
        const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
        if (mq.addEventListener) mq.addEventListener('change', handler);
        else mq.addListener(handler as any);
        return () => {
            if (mq.removeEventListener) mq.removeEventListener('change', handler);
            else mq.removeListener(handler as any);
        };
    }, []);

    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            {isDesktop ? <DesktopPolicy /> : <MobilePolicy />}
        </Suspense>
    );
}
