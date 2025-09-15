interface SecureModeStripProps {
  enabled: boolean;
}

export default function SecureModeStrip({ enabled }: SecureModeStripProps) {
  if (!enabled) return null;
  return (
    <div className="w-full bg-blue-600 text-white px-3 py-2 sm:px-4 text-center text-xs sm:text-sm font-medium mb-2 rounded-xl shadow-lg">
      🔒 SECURE TEST MODE - Navigation shortcuts are restricted during the exam
    </div>
  );
}
