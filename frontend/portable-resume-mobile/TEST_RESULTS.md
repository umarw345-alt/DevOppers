# Verification of the corrected copy

Checked November 1, 2026 in Linux using Node 24.22.1, npm 11.9.0, Expo 58.0.22, React Native 0.88.1, React 19.3.0 and TypeScript 7.0.2.

| Check | Result |
| --- | --- |
| Clean installation from package-lock.json (`npm ci`) | Passed |
| Strict TypeScript with Expo configuration (`npm run typecheck`) | Passed, zero errors |
| Automated regression tests (`npm test`) | 25 passed |
| Android production JavaScript/Hermes export | Passed |
| iOS production JavaScript/Hermes export | Passed |

## Regression coverage

1. Resume conversion trims names and splits skills/bullets.
2. Sample extraction works offline and returns independent data.
3. Offline template fetching falls back to defaults.
4. Offline login explains the connection failure.
5. Login rejects a missing token.
6. Registration without a token requires separate login.
7. Authenticated previews send the bearer token.
8. Malformed template responses fall back.
9. HTTP template errors fall back.
10. Empty and duplicate template lists are handled.
11. Preview validation errors are surfaced.
12. Empty preview responses are rejected.
13. Request timeouts reject and clean up their timer.
14. File picker failures are displayed without escaping the handler.
15. Canceling the picker leaves Continue disabled when there is no resume.
16. Demo upload, name editing and template navigation work.
17. Back preserves the edited resume and Continue remains available.
18. Tapping the selected template keeps its preview visible.
19. A failed replacement preview clears the old preview.
20. Save failures keep the draft and allow retry.
21. Saving retains resume content and the selected accent/font.
22. Restarting restores the saved portfolio.
23. Delete failures preserve the list.
24. Deleting all portfolios keeps the list empty after restart.
25. Unreadable saved data is not overwritten and retry works.

## Limits of these checks

The regression suite substitutes native controls, file selection, storage and API responses with controlled test versions. Expo exports validate dependency resolution and JavaScript/Hermes bundling; they are not native APK/IPA builds or tests on a phone. Actual touch layout, keyboard behavior, safe areas, WebView rendering, Expo Go compatibility on the user's phone, and live backend contracts still require device/integration testing.

No test can guarantee an application is free of all bugs. Existing unfinished backend features are described in README.md.
