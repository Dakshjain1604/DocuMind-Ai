# DocuMind frontend

Next.js 15 (App Router, React 19). See the [root README](../README.md) for the
architecture and full setup.

```bash
npm install
cp .env.example .env      # JWT_SECRET is required
npm run dev               # http://localhost:3000
```

The backend must be running on `RAG_BACKEND_URL` (default
`http://localhost:8000`) for anything under `/Dashboard` to work.

```bash
npx tsc --noEmit          # typecheck
npm run lint
npm run build
```

## Layout

```
app/
  page.tsx            landing page; reads live telemetry from the backend
  Dashboard/          the application shell
    page.tsx          composition + view switching
    types.ts          ApiEnvelope, Coverage, AuditFinding, Slide, Citation…
  components/         ChatStream, GraphView, QuizArena, MasterclassStudio,
                      MermaidDiagram, CitationChip, HomeCard, AuthShell
  api/rag/            proxy routes to the backend
    _lib/proxy.ts     the only place that talks to RAG_BACKEND_URL
  api/auth/           signup / signin / signout
components/ui/        button, card, badge, input, skeleton, ErrorBanner
lib/
  sse.ts              SSE frame parsing + sseFetch (fetch + stream reader)
  formatSummary.ts    summary markdown normalisation
  useCopyFeedback.ts  the copy-button "check then revert" state, once
  auth.ts             JWT secret resolution (throws if unset); iss/aud constants
  userStore.ts        accounts: Mongo when configured, JSON file otherwise
  mongodb.ts          singleton Mongo connection
middleware.ts         verifies the session cookie; gates /Dashboard and the
                      /api/rag/documents|graph|trace proxy routes (401 for APIs)
```

`@/*` resolves from the `frontend/` root (see `tsconfig.json`), so
`@/components/ui/button` is `frontend/components/ui/button.tsx` — not the
`app/components/` directory.

## Conventions

- **Never call the backend directly from a component.** Everything goes through
  `app/api/rag/*`, which all route through `_lib/proxy.ts` — that is where the
  base URL, timeouts, error envelope and SSE headers live.
- **Read SSE with `lib/sse.ts`.** Frame-boundary handling is subtle enough that
  it should exist once. Streaming panels call `sseFetch(...)`, which attaches
  the caller's `AbortSignal` to the underlying request so a cancelled stream
  actually closes the upstream connection.
- **Distinguish empty from failed.** `ErrorBanner` and `EmptyState` are separate
  components on purpose: "no findings in this document" and "the analysis could
  not run" must not look alike. Render `CoverageNote` alongside any generated
  artifact so the sampling is visible.

## Manual smoke test

With both services running and a document indexed:

1. `/` — telemetry shows real numbers, or `—` with an OFFLINE badge when the
   backend is down
2. Navigate straight to `/Dashboard` — redirects to `/signin`
3. Sign up, sign in
4. Upload by drag-drop **and** by tabbing to the dropzone and pressing Enter
5. Queue a 6th file — rejected cleanly; queue count and "Index N file(s)"
   button agree
6. Index — the progress log fills with real stage names and chunk counts, and
   shows an amber warning if graph sampling kicks in
7. Library shows the filename, not the hash
8. Summary renders formatted markdown; copy and export work
9. Query console streams; citation chips are clickable
10. Quiz: answer three, hit Reset — all cards clickable again, no answers shown
11. Masterclass: switch chapters rapidly — one coherent draft, not interleaved
12. Audit / Audio / Slides — real content with the coverage caveat beneath

**Honesty check:** point `RAG_BACKEND_URL` at a closed port and click every
studio card. Each panel must show an error banner. None may show plausible
content.
