// Finance Studio React entry point

import React from 'react';
import { createRoot } from 'react-dom/client';
import { FinanceStudioPage } from './FinanceStudioPage';
import './styles.css';

export function initFinanceStudio() {
  const rootElement = document.getElementById('finance-studio-root');
  if (!rootElement) {
    console.error('Finance Studio root element not found');
    return;
  }

  const root = createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <FinanceStudioPage />
    </React.StrictMode>
  );
}

// Auto-initialize if root exists
if (document.getElementById('finance-studio-root')) {
  initFinanceStudio();
}

