# Codex Task M5 — GitHub and Vercel Portfolio Deployment

Implement M5 only after the web app builds locally and the GLB viewer has been exercised.

## Read first

Read the repository README, web package scripts, GLB export documentation and docs/tasks/04-web-walkthrough.md.

## Goal

Publish the interactive dream-home viewer as a maintainable portfolio project using GitHub and Vercel.

## Requirements

1. Inspect the existing repository and portfolio structure before making deployment assumptions. Preserve the app as a static frontend unless a real need for a backend is identified.
2. Ensure the web app has a documented local development command and a deterministic production build.
3. If web/ is the Vercel root, document/set the project root directory, install command, build command and output directory correctly.
4. Keep credentials and environment-specific values out of source control. No secrets are needed for the basic static viewer.
5. Keep .blend, GLB and texture sizes under review. Use Git LFS for suitable source assets if useful; for large deployment assets, evaluate an appropriate public asset-hosting option before adding them.
6. Do not commit temporary renders, caches, node_modules, build output or unrelated local files.
7. Add a lightweight CI workflow only if it adds practical value: at minimum install dependencies and run checks/build on pull requests.
8. Test the production build locally; verify model paths work with the Vercel deployment root and any configured base path.
9. Document the GitHub-to-Vercel connection and the manual checks needed after first deployment.
10. Do not claim deployment succeeded unless a deployment URL/status has been observed.

## Acceptance criteria

- Clean checkout has documented install, dev and build commands.
- Production build passes.
- Deployment settings are documented and the Vercel project is connected or the exact remaining manual steps are listed.
- First-load performance, mobile behavior, model loading and navigation are checked against the deployed version where access permits.
- No secrets or unnecessary infrastructure are introduced.

## Report back

Provide the commit/branch, build and test results, deployment URL if one exists, asset-size findings, and any remaining manual setup. Never invent a deployment URL or report a deployment as successful without verification.
