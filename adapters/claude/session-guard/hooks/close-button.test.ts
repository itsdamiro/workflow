import { expect, test } from 'claude-code/testing'

// The Close slice button, pressed on each surface that takes presses: the band draws once the context passes the
// soft limit, and the press submits the handoff prompt as the owner.
for (const surface of ['terminal', 'desktop'] as const) {
  test(`Close slice submits the handoff prompt on ${surface}`, async ($, on) => {
    const submitted: string[] = []
    on('session.usage', () => ({
      value: { startedAt: 0, context: { tokens: 160000, window: 1000000 }, rateLimits: [] },
    }))
    on('command.run', (_$, e) => {
      submitted.push(`/${e.command}${e.args ? ` ${e.args}` : ''}`)
      return { value: { text: '' } }
    })

    on('session.start', () => ({ cwd: '/tmp' }))
    on('ui.toast', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))

    await $.session.start({ cwd: '/tmp' })
    const band = await $.ui.mount({
      plugin: 'session-guard',
      surface,
      component: 'AbovePrompt',
      props: { hasSurvey: false, isWorking: false },
    })
    expect(await band.find({ key: 'close' })).toBeDefined()
    await band.press({ key: 'close' })
    expect(submitted).toEqual(['/handoff'])
    await band.unmount()
  })
}
