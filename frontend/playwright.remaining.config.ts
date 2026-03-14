import base from './playwright.config';

/**
 * Same as default config but excludes smoke tests (auth, navigation, upload).
 * Used in CI to run "remaining" E2E tests after the smoke suite.
 */
export default {
  ...base,
  testIgnore: [
    '**/auth.spec.ts',
    '**/navigation.spec.ts',
    '**/upload.spec.ts',
  ],
};
