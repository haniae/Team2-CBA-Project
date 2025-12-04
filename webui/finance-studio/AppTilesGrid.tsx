// App tiles grid component

import React from 'react';
import type { FinanceStudioAppId } from './types';

interface AppTile {
  id: FinanceStudioAppId;
  title: string;
  description: string;
  icon: string;
  color: string;
}

const APP_TILES: AppTile[] = [
  {
    id: 'data-consolidation',
    title: 'Data Consolidation Studio',
    description: 'Transform raw data from multiple sources into a clean, standardized finance table you can trust.',
    icon: '📊',
    color: '#0066FF',
  },
  {
    id: 'board-reports',
    title: 'Board-Ready Reports',
    description: 'Generate 3-statement, board-ready reports with real-time BvA and drill-down to transaction level.',
    icon: '📋',
    color: '#0f766e',
  },
  {
    id: 'visualization',
    title: 'Visualization Studio',
    description: 'Interactive charts and dashboards with drill-down from KPI to transaction detail.',
    icon: '📈',
    color: '#8b5cf6',
  },
  {
    id: 'three-statement',
    title: '3-Statement Modeling Studio',
    description: 'One governed model for P&L, balance sheet, and cash flow across entities, currencies, and hierarchies.',
    icon: '💼',
    color: '#f59e0b',
  },
  {
    id: 'entity-rollup',
    title: 'Entity Rollup & Drilldown',
    description: 'Roll up multiple subsidiaries or regions into a single P&L, with drill-down on demand.',
    icon: '🏢',
    color: '#10b981',
  },
  {
    id: 'export-bridge',
    title: 'Export & BI Bridge',
    description: 'Export consolidated tables into Excel, CSV, or BI tools with one click.',
    icon: '📤',
    color: '#ef4444',
  },
];

interface AppTilesGridProps {
  onLaunchApp: (appId: FinanceStudioAppId) => void;
}

export function AppTilesGrid({ onLaunchApp }: AppTilesGridProps) {
  return (
    <div className="app-tiles-grid">
      {APP_TILES.map((tile) => (
        <div key={tile.id} className="app-tile">
          <div
            className="app-tile-icon"
            style={{ backgroundColor: `${tile.color}15`, color: tile.color }}
          >
            <span className="app-tile-icon-emoji">{tile.icon}</span>
          </div>
          <div className="app-tile-content">
            <h3 className="app-tile-title">{tile.title}</h3>
            <p className="app-tile-description">{tile.description}</p>
            <button
              className="app-tile-launch-button"
              onClick={() => onLaunchApp(tile.id)}
              style={{ backgroundColor: tile.color }}
            >
              Launch
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

