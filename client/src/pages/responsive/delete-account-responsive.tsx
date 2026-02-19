import React, { Suspense, useEffect, useState } from 'react';

const MobileDeleteAccount = React.lazy(() => import('../mobile/delete-account'));
const DesktopDeleteAccount = React.lazy(() => import('../desktop/delete-account-desktop'));

export default function DeleteAccountResponsive(): JSX.Element {
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
            {isDesktop ? <DesktopDeleteAccount /> : <MobileDeleteAccount />}
        </Suspense>
    );
}
