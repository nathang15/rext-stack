import React, { useState, useEffect, lazy, Suspense } from 'react';
import LoadingScreen, { ErrorScreen } from './components/LoadingScreen';
import './styles/App.css';

const Search = lazy(() => import('./components/Search'));
const Background = lazy(() => import('./components/Background'));

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await fetch('http://127.0.0.1:5000/search/false/null/0/%20');
        
        if (response.ok) {
          const data = await response.json();
          if (Array.isArray(data.documents)) {
            setIsLoading(false);
            setError(null);
          } else {
            throw new Error('Invalid response format');
          }
        } else {
          throw new Error(`Backend returned ${response.status}`);
        }
      } catch (error) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
        }, 1000);
      }
    };

    if (isLoading) {
      checkBackendStatus();
    }
  }, [isLoading, retryCount]);

  const handleRetry = () => {
    setError(null);
    setRetryCount(0);
    setIsLoading(true);
  };

  if (error) {
    return <ErrorScreen error={error} onRetry={handleRetry} />;
  }

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <div className="App">
      <Suspense fallback={<LoadingScreen />}>
        <Background />
        <div className="content-wrapper">
          <Search />
        </div>
      </Suspense>
    </div>
  );
}

export default App;