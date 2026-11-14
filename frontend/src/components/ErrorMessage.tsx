import React from 'react';
import { AlertCircle } from 'lucide-react';

export const ErrorMessage: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="flex items-start gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4">
    <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
    <div className="flex-1">
      <p className="text-sm text-rose-300">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 text-xs font-medium text-rose-400 hover:text-rose-300 underline cursor-pointer">
          Try again
        </button>
      )}
    </div>
  </div>
);
