import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    Share2,
    Copy,
    Trophy,
    Target,
    BookOpen
} from 'lucide-react';

/**
 * Share Component
 *
 * A comprehensive sharing component for the CBT platform
 * Allows users to share achievements, test results, and app content
 */
interface ShareProps {
    title?: string;
    description?: string;
    url?: string;
    type?: 'achievement' | 'result' | 'progress' | 'app';
    score?: number;
    subject?: string;
    className?: string;
}

const Share: React.FC<ShareProps> = ({
    title = "Check out my NEET preparation progress!",
    description = "I'm preparing for NEET 2026 with InzightEd. Join me on this journey!",
    url = window.location.origin,
    type = 'app',
    score,
    subject,
    className = ""
}) => {
    const [copied, setCopied] = useState(false);

    // Generate share content based on type
    const getShareContent = () => {
        switch (type) {
            case 'achievement':
                return {
                    title: `🏆 Achievement Unlocked! ${score ? `Scored ${score}%` : ''}`,
                    description: `I just achieved a milestone in my NEET preparation! ${subject ? `in ${subject}` : ''}`,
                    emoji: '🏆'
                };
            case 'result':
                return {
                    title: `📊 Test Result: ${score ? `${score}%` : 'Completed'}`,
                    description: `Just completed a ${subject || 'practice'} test. ${score ? `Scored ${score}%!` : 'Keep practicing!'} `,
                    emoji: '📊'
                };
            case 'progress':
                return {
                    title: `📈 Study Progress Update`,
                    description: `Making great progress in my NEET preparation journey! ${score ? `${score}% complete` : ''}`,
                    emoji: '📈'
                };
            default:
                return {
                    title,
                    description,
                    emoji: '🎯'
                };
        }
    };

    const shareContent = getShareContent();
    const shareText = `${shareContent.emoji} ${shareContent.title}\n\n${shareContent.description}\n\n${url}`;

    // Copy to clipboard
    const copyToClipboard = async () => {
        try {
            await navigator.clipboard.writeText(shareText);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    // Share via WhatsApp
    const shareViaWhatsApp = () => {
        const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
        window.open(whatsappUrl, '_blank');
    };

    // Native Web Share API (if supported)
    const shareNative = async () => {
        if ('share' in navigator) {
            try {
                await navigator.share({
                    title: shareContent.title,
                    text: shareContent.description,
                    url: url,
                });
            } catch (err) {
                console.log('Error sharing:', err);
            }
        }
    };

    const shareOptions = [
        {
            name: 'Copy Link',
            icon: Copy,
            action: copyToClipboard,
            color: 'bg-white/10 border-white/20 text-white hover:bg-white/20',
            available: true
        }
    ];

    return (
        <div className={`px-4 mb-3 ${className}`}>
            <Card className="bg-white backdrop-blur-xl border border-white/10 shadow-2xl">
                <CardHeader className='py-3 px-4'>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div>
                                <CardTitle className="text-lg font-semibold text-gray-800">
                                    Study with your friends
                                </CardTitle>
                                <p className="text-sm text-gray-600">Share with your friends and prepare with them together</p>
                            </div>
                        </div>
                        {type !== 'app' && (
                            <Badge variant="secondary" className="bg-white/10 text-white border-white/20">
                                {type === 'achievement' && <Trophy className="w-3 h-3 mr-1" />}
                                {type === 'result' && <Target className="w-3 h-3 mr-1" />}
                                {type === 'progress' && <BookOpen className="w-3 h-3 mr-1" />}
                                {type.charAt(0).toUpperCase() + type.slice(1)}
                            </Badge>
                        )}
                    </div>
                </CardHeader>

                <CardContent>

                    {/* Share Buttons */}
                    <div className="grid grid-cols-2 gap-3">

                        {/* Native Share Button */}
                        {'share' in navigator && (
                            <Button
                                variant="secondary"
                                size="sm"
                                onClick={shareNative}
                                className="bg-black text-white"
                            >
                                <Share2 />Share with friends
                            </Button>
                        )}
                        {shareOptions.map((option) => (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={shareNative}
                            >
                                <option.icon />Copy Link
                            </Button>
                        ))}


                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default Share;
