import React from 'react';
import Search from './components/Search';
import Background from './components/Background';
import './styles/App.css';

function App() {
  return (
    <div className="App">
      <Background />
      <div className="content-wrapper">
        <Search />
      </div>
    </div>
  );
}

export default App;