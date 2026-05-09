import { useState } from 'react';
import Header from './components/Header.jsx';
import TripInput from './components/TripInput.jsx';
import TripResult from './components/TripResult.jsx';
import { generateTrip } from './services/api.js';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleGenerate = async (userInput) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await generateTrip(userInput);
      setResult(data);
    } catch (err) {
      setError(err.message || '生成行程时出错，请稍后重试。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        <div className="app-panel app-panel--input">
          <TripInput onSubmit={handleGenerate} isLoading={loading} />
        </div>
        <div className="app-panel app-panel--result">
          <TripResult result={result} isLoading={loading} error={error} />
        </div>
      </main>
    </div>
  );
}

export default App;