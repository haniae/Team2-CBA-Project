// Finance Studio main page component

import React, { useState } from 'react';
import type { FinanceStudioAppId } from './types';
import { AppTilesGrid } from './AppTilesGrid';
import { DataConsolidationStudio } from './apps/DataConsolidationStudio';
import { BoardReadyReports } from './apps/BoardReadyReports';
import { VisualizationStudio } from './apps/VisualizationStudio';
import { ThreeStatementModeling } from './apps/ThreeStatementModeling';
import { EntityRollup } from './apps/EntityRollup';
import { ExportBridge } from './apps/ExportBridge';

export function FinanceStudioPage() {
  const [activeApp, setActiveApp] = useState<FinanceStudioAppId | null>(null);

  const handleLaunchApp = (appId: FinanceStudioAppId) => {
    setActiveApp(appId);
  };

  const handleBackToTiles = () => {
    setActiveApp(null);
  };

  if (activeApp) {
    return (
      <div className="finance-studio-app-view">
        <div className="finance-studio-header">
          <button
            onClick={handleBackToTiles}
            className="back-button"
            aria-label="Back to app tiles"
          >
            ← Back
          </button>
          <h1>Finance Studio</h1>
        </div>
        <div className="finance-studio-app-content">
          {activeApp === 'data-consolidation' && (
            <DataConsolidationStudio />
          )}
          {activeApp === 'board-reports' && <BoardReadyReports />}
          {activeApp === 'visualization' && <VisualizationStudio />}
          {activeApp === 'three-statement' && <ThreeStatementModeling />}
          {activeApp === 'entity-rollup' && <EntityRollup />}
          {activeApp === 'export-bridge' && <ExportBridge />}
        </div>
      </div>
    );
  }

  return (
    <div className="finance-studio-landing">
      <div className="finance-studio-header-section">
        <h1>Finance Studio</h1>
        <p className="finance-studio-subtitle">
          Interactive apps for consolidation, reporting, visualization, and modeling.
        </p>
      </div>
      <AppTilesGrid onLaunchApp={handleLaunchApp} />
    </div>
  );
}

