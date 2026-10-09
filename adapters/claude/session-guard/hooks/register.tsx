import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { GuardLevel, GuardUsage } from '../types'

const usage = atom({ plugin: 'session-guard', key: 'usage' } as const, null)
const dismissed = atom({ plugin: 'session-guard', key: 'dismissed' } as const, 'ok' as GuardLevel)

const RANK: Record<GuardLevel, number> = { ok: 0, soft: 1, hard: 2 }
// The same values are declared in .claude-plugin/plugin.json (the config menu and the host read them there);
// test_defaults.py fails when the two differ.
const DEFAULTS = {
  softTokens: 150000,
  hardTokens: 200000,
  limitPercent: 80,
  handoffPrompt: '/handoff', // the one entry point: the handoff skill, which follows docs/sop/handoff.md (reviews and fresh-reader check included, ADR 005)
}

const k = (n: number) => `${Math.round(n / 1000)}k`

type Opts = typeof DEFAULTS

const levelOf = (tokens: number | null, opt: Opts): GuardLevel =>
  tokens === null ? 'ok' : tokens >= opt.hardTokens ? 'hard' : tokens >= opt.softTokens ? 'soft' : 'ok'

async function refresh($: EngineInterface, opt: Opts, warnedLimits: Set<string>) {
  const { context, rateLimits } = await $.session.usage()
  const tokens = context.tokens ?? null
  const next: GuardUsage = {
    tokens,
    level: levelOf(tokens, opt),
    limits: rateLimits.map(l => ({ kind: l.kind, percent: l.percentUsed })),
  }
  const before = await read($, usage)
  await update($, usage, () => next)

  if (next.level === 'ok') {
    await update($, dismissed, () => 'ok' as GuardLevel) // a fresh or compacted session starts over
  } else if (RANK[next.level] > RANK[before?.level ?? 'ok']) {
    $.ui.toast(
      next.level === 'hard'
        ? `Context ${k(tokens ?? 0)}: close the slice and start fresh`
        : `Context ${k(tokens ?? 0)}: a good time to close the slice`,
      { timeoutMs: 8000 },
    )
  }
  for (const l of next.limits) {
    if (l.percent >= opt.limitPercent && !warnedLimits.has(l.kind)) {
      warnedLimits.add(l.kind)
      $.ui.toast(`${l.kind.replace('_', ' ')} limit ${Math.round(l.percent)}% used`, { timeoutMs: 8000 })
    }
  }

  const five = next.limits.find(l => l.kind === 'five_hour')
  $.ui.status(tokens === null ? undefined : `ctx ${k(tokens)}${five ? ` · 5h ${Math.round(five.percent)}%` : ''}`)
}

export const register: Register = (on, options) => {
  const opt: Opts = { ...DEFAULTS, ...(options as Partial<Opts>) }
  const warnedLimits = new Set<string>()

  on('session.start', async ($, e, next) => {
    await refresh($, opt, warnedLimits)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($, opt, warnedLimits)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const u = await read($, usage)
    const dis = await read($, dismissed)
    const hot = u?.limits.filter(l => l.percent >= opt.limitPercent) ?? []
    const showContext = u !== null && RANK[u.level] > RANK[dis]

    if (e.props.hasSurvey || u === null || (!showContext && hot.length === 0)) {
      return next(e)
    }

    const { Box, Button, Text } = $.ui.resolve(e)
    const urgent = u.level === 'hard'

    return (
      <Box>
        {showContext ? (
          <Text color={urgent ? 'red' : 'yellow'}>
            Context {k(u.tokens ?? 0)} (limit {k(urgent ? opt.hardTokens : opt.softTokens)}).{' '}
          </Text>
        ) : null}
        {hot.map(l => (
          <Text key={l.kind} color="yellow">
            {l.kind.replace('_', ' ')} {Math.round(l.percent)}%.{' '}
          </Text>
        ))}
        {showContext ? (
          <Button
            key="close"
            label="Close slice"
            onPress={async () => {
              await update($, dismissed, () => u.level)
              await $.prompt.submit({ text: opt.handoffPrompt, asUser: true })
            }}
          />
        ) : null}
        {showContext ? (
          <Button key="later" label="Later" onPress={() => update($, dismissed, () => u.level)} />
        ) : null}
      </Box>
    )
  })
}
