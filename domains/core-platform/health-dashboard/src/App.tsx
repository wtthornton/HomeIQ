import { Dashboard } from './components/Dashboard';
import { ThemeProvider } from './components/ThemeContext';

function App(): JSX.Element {
  return (
    <ThemeProvider>
      <Dashboard />
    </ThemeProvider>
  );
}

export default App;
