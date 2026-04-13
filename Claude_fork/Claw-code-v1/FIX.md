# FIX

## What I fixed
- Replaced the invalid Commander short option definition for `-d2e` with a valid long option and added argv normalization so legacy `-d2e` still works.
- Skipped the forced minimum-version update gate for local leaked/dev builds (`0.0.0-*`) so the bundled CLI can actually run in this repo.
- Updated the bundle script so the built `dist/cli.mjs` works under Node for startup/help paths by externalizing `@anthropic-ai/sdk` and injecting `createRequire` into the ESM banner.
- Replaced direct `React.useEffectEvent` usage with a compatibility hook so interactive startup no longer crashes on `bun dist/cli.mjs`.

## Files changed
- `scripts/build-bundle.ts`
- `src/entrypoints/cli.tsx`
- `src/main.tsx`
- `src/utils/autoUpdater.ts`
- `src/hooks/useEffectEventCompat.ts`
- `src/state/AppState.tsx`
- `src/components/tasks/BackgroundTasksDialog.tsx`

## Smoke tests
- `bun run build` ✅
- `bun dist/cli.mjs --version` ✅
- `bun dist/cli.mjs --help` ✅
- `bun dist/cli.mjs -d2e --version` ✅
- `bun dist/cli.mjs -p --bare --dangerously-skip-permissions --max-turns 1 "Reply with exactly OK."` ✅ (`OK`)
- `bun dist/cli.mjs -p --bare --dangerously-skip-permissions --output-format json --max-turns 1 "Return the word hi."` ✅
- `bun dist/cli.mjs` ✅ reaches the workspace trust prompt instead of crashing
- `node dist/cli.mjs --version` ✅
- `node dist/cli.mjs --help` ✅
- `node dist/cli.mjs -d2e --version` ✅

## Notes
- `npm run check` is still not green in this leaked checkout because the repo has thousands of existing Biome/TypeScript errors outside the repaired runtime path; this fix focused on getting the CLI build and happy-path execution working.
