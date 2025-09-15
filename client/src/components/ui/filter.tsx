import React from 'react';

interface BottomSheetModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm?: () => void;
    title?: string;
    children: React.ReactNode;
}

const BottomSheetModal: React.FC<BottomSheetModalProps> = ({
    isOpen,
    onClose,
    onConfirm,
    title = "Modal",
    children
}) => {
    const handleConfirm = () => {
        if (onConfirm) onConfirm();
        onClose();
    };

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
                    onClick={onClose}
                />
            )}

            {/* Modal */}
            <div
                className={`fixed bottom-0 left-0 right-0 bg-white rounded-t-lg shadow-lg z-50 transform transition-transform duration-300 ease-in-out md:hidden ${isOpen ? 'translate-y-0' : 'translate-y-full'
                    }`}
                style={{ maxHeight: '80vh', overflowY: 'auto' }}
            >
                <div className="p-4">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">{title}</h2>
                        <button
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            ✕
                        </button>
                    </div>

                    {/* Custom Content */}
                    <div className="space-y-4">
                        {children}
                    </div>

                    {/* Buttons */}
                    <div className="flex space-x-2 mt-6">
                        <button
                            onClick={onClose}
                            className="flex-1 py-2 px-4 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                        >
                            Cancel
                        </button>
                        {onConfirm && (
                            <button
                                onClick={handleConfirm}
                                className="flex-1 py-2 px-4 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                            >
                                Confirm
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
};

export default BottomSheetModal;
