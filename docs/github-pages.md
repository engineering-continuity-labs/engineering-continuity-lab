# GitHub Pages demo

The public demo deploys `ui/dist` with GitHub Actions whenever `main` changes. In the repository settings, configure **Pages** to use **GitHub Actions** as its source. Once the first deployment completes, the expected URL is:

<https://engineering-continuity-labs.github.io/engineering-continuity-lab/>

The artifact is static HTML, CSS, and JavaScript. Asset paths are relative so it works under the repository Pages subpath. No build tool, server, credentials, analytics, cookies, or external data service is involved.

The default bundled report is **Atlas Commerce · SYNTHETIC**, generated from project-owned events using existing Git/review/traceability/verification derivation. Run `python scripts/generate_showcase.py --check` to verify freshness. A separate **Public eShop Validation Sample** retains the static Git-evidence sample generated from the documented dotnet/eShop validation revision. It contains no eShop source code and the page does not contact or clone eShop. Visitors can choose a compatible local report JSON; the browser validates and holds it only in page memory. The page never uploads or persists that selected file. `continuity explorer` remains a separate loopback-only local workflow for repository analysis.
