import React from 'react';

const LoadingScreen = () => (
  <div className="loading-container">
    <div className="loading-dots">
      {[...Array(196)].map((_, index) => {
        const x = index % 14;
        const y = Math.floor(index / 14);
        return (
          <div
            key={index}
            className="loading-dot"
            style={{
              left: `${x * 28}px`,
              top: `${y * 28}px`,
              animation: `pulse 2s ease-in-out infinite`,
              animationDelay: `${(x + y) * 0.1}s`
            }}
          />
        );
      })}
    </div>
    <div className="loading-text">LOADING</div>
  </div>
);


export const ErrorScreen = ({ error, onRetry }) => (
  <div className="fixed inset-0 flex items-center justify-center bg-gray-900">
    <div className="bg-gray-800 p-8 rounded-lg shadow-xl text-center max-w-md">
      <div className="text-red-500 mb-4">
        <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
          />
        </svg>
      </div>
      <h2 className="text-2xl font-bold text-white mb-4">Error</h2>
      <p className="text-gray-400 mb-6">{error}</p>
      <button
        onClick={onRetry}
        className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
      >
        Retry
      </button>
    </div>
  </div>
);

export default LoadingScreen;