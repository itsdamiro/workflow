export type GuardLevel = 'ok' | 'soft' | 'hard'
export type GuardLimit = { kind: string; percent: number }
export type GuardUsage = { tokens: number | null; level: GuardLevel; limits: GuardLimit[] }

declare module 'claude-code' {
  interface PluginState {
    'session-guard': { usage: GuardUsage | null; dismissed: GuardLevel }
  }
}
