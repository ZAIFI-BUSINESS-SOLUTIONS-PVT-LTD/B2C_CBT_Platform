import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/**
 * NEET Exam Countdown Component
 *
 * A black glassmorphic countdown card with modern dark design
 */
const NeetCountdown: React.FC = () => {
    // Calculate days remaining until NEET exam (May 3, 2026)
    const calculateDaysLeft = (): number => {
        const neetDate = new Date('2026-05-03');
        const today = new Date();
        const timeDiff = neetDate.getTime() - today.getTime();
        const daysLeft = Math.ceil(timeDiff / (1000 * 3600 * 24));
        return Math.max(0, daysLeft);
    };

    const daysLeft = calculateDaysLeft();

    return (
        <div className="my-3">
            <Card className="bg-black/70 backdrop-blur-xl shadow-2xl">
                <CardHeader className='py-2 px-3'>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div>
                                <CardTitle className="text-lg font-semibold text-white">
                                    NEET 2026
                                </CardTitle>
                                <p className="text-sm text-gray-300">Exam date: May 3, 2026</p>
                            </div>
                        </div>
                        <Badge variant="secondary" className="bg-white/10 text-blue-500 border-blue-500 backdrop-blur-sm pt-1">
                            {daysLeft === 1 ? '1 Day Left' : `${daysLeft} Days Left`}
                        </Badge>
                    </div>
                </CardHeader>
            </Card>
        </div>
    );
};

export default NeetCountdown;
