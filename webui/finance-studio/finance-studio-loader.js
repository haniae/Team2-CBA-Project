// Finance Studio loader - compiles and loads React components
// This is a simplified loader that works with the existing setup

// Since we're using TypeScript/JSX, we'll need to either:
// 1. Use a bundler (webpack/vite) to compile
// 2. Use Babel standalone to transpile JSX
// 3. Use React.createElement directly

// For now, we'll create a simple loader that uses React.createElement
// In production, you'd want to use a proper build system

import { initFinanceStudio } from './index.tsx';

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initFinanceStudio();
  });
} else {
  initFinanceStudio();
}

