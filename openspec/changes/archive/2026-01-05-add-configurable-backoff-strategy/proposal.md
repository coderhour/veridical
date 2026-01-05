# Proposal: Add Configurable Backoff Strategy

## Summary

Add a configuration option to select the polling backoff strategy (`constant` or `exponential`) and change the default from `exponential` to `constant`.

## Why

The current implementation uses exponential backoff for polling Jules sessions, which causes significant delays in detecting session completion:

- With a 30-second `poll_interval`, exponential backoff calculates delays as: 30s → 60s → 120s → 240s (capped at 300s)
- This means if a session completes after the 3rd poll, the user waits up to 2 minutes before detection
- Users report delays of ~4 minutes when expecting ~30 second responsiveness

Exponential backoff is designed to reduce API load during thundering herd scenarios. However, Veridical operates as a single client polling its own session, making this optimization unnecessary and counterproductive to user experience.

## What Changes

1. **Add `backoff_strategy` config option** to `JulesConfig` with values `constant` (default) or `exponential`
2. **Modify Poller** to use the configured strategy instead of hardcoded `ExponentialBackoff`
3. **Update config templates** to document the new option
4. **Update poller spec** to reflect the configurable, defaulting-to-constant behavior

## Impact

- **User Experience**: Session completion detected consistently at configured `poll_interval` (default 30s)
- **Backward Compatibility**: Users who prefer exponential backoff can set `backoff_strategy: exponential`
- **Specs Affected**: `poller`, `config`

## Alternatives Considered

1. **Just change the default** - Does not allow users who want exponential backoff to configure it
2. **Add more granular backoff settings** (multiplier, max jitter) - Overkill for this use case; exponential strategy already has sensible internal defaults
