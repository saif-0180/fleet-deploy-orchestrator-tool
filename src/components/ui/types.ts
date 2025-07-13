
export type DeploymentStatus = 'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed';

export interface LogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'error' | 'warning' | 'debug';
}
