# NestJS Template

This is a simple Nest.js starter template with some common configured items.

## OCR Microservice

The OCR microservice is isolated in `ocr-service/` for cleaner VPS deployment.

- Service docs: `ocr-service/README.md`
- Compose service name: `ocr`
- Default port: `8000`

### Configured items

- Prettier
- EsLint
- Commit-lint
- Winston(logging)
- Global exception filter
- Helmet
- Throttler
- CORS with allowed origins
- Swagger documentation
- Husky(with commit lint and pretty quick)

## Smoke E2E test

Run the backend server and then execute the smoke E2E script.

1. Copy `.env.example` to `.env` if needed.
2. Set `SMOKE_TELEGRAM_FILE_ID` in `.env`.
3. Optionally set:
    - `SMOKE_APP_BASE_URL` (defaults to `APP_BASE_URL` or `http://127.0.0.1:${PORT}`)
    - `SMOKE_WAIT_FOR_BACKEND_MS` (how long to wait for `/health`)
    - `SMOKE_TIMEOUT_MS` (overall smoke test timeout)
4. Run:

```bash
pnpm run smoke:e2e
```

If you start the server in parallel, use:

```bash
pnpm run smoke:e2e:wait
```

Equivalent npm scripts are also available: `npm run test:smoke:e2e` and `npm run test:smoke:e2e:wait`.

If `/transactions` returns `500` during smoke test, run DB migrations first:

```bash
pnpm run db:migrate
```

For a one-command setup + smoke run:

```bash
pnpm run smoke:e2e:setup
```
