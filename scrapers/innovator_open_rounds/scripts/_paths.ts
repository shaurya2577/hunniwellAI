import os from 'node:os';
import path from 'node:path';

export const REPO_ROOT = process.cwd();

export function downloadsOpenRoundsRoot() {
  return path.join(os.homedir(), 'Downloads', 'openRounds');
}

export function runOutputDir(runId: string) {
  return path.join(downloadsOpenRoundsRoot(), runId);
}

export function storageStatePath() {
  return path.join(REPO_ROOT, '.auth', 'storageState.json');
}

export function ensurePosixUrl(baseUrl: string, maybeRelative: string) {
  if (/^https?:\/\//i.test(maybeRelative)) return maybeRelative;
  const b = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const r = maybeRelative.startsWith('/') ? maybeRelative : `/${maybeRelative}`;
  return `${b}${r}`;
}
