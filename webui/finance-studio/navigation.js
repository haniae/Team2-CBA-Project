// Finance Studio navigation integration
// This should be called from app.js or added to the existing navigation handlers

export function setupFinanceStudioNavigation() {
  // Handle Finance Studio button click
  const financeStudioButton = document.getElementById('finance-studio-button');
  const financeStudioView = document.getElementById('finance-studio-view');
  const chatPanel = document.querySelector('.chat-panel');
  const chatsView = document.getElementById('chats-view');
  const utilityPanel = document.getElementById('utility-panel');

  if (financeStudioButton && financeStudioView) {
    financeStudioButton.addEventListener('click', () => {
      // Hide other views
      if (chatPanel) chatPanel.classList.add('hidden');
      if (chatsView) chatsView.classList.add('hidden');
      if (utilityPanel) utilityPanel.classList.add('hidden');

      // Show Finance Studio view
      financeStudioView.classList.remove('hidden');

      // Initialize React app if not already initialized
      if (document.getElementById('finance-studio-root') && !window.financeStudioInitialized) {
        // Load Finance Studio React app
        import('./index.tsx').then((module) => {
          module.initFinanceStudio();
          window.financeStudioInitialized = true;
        }).catch((err) => {
          console.error('Failed to load Finance Studio:', err);
        });
      }
    });
  }

  // Also handle data-action attribute for consistency
  document.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action="open-finance-studio"]');
    if (target) {
      e.preventDefault();
      if (financeStudioButton) {
        financeStudioButton.click();
      }
    }
  });
}

// Auto-setup when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupFinanceStudioNavigation);
} else {
  setupFinanceStudioNavigation();
}

