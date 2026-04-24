# Deploy SmartCal@EG na Fly.io — stan aktualny

## Apps (wszystkie region `fra`, org `personal`)

| Rola | App | Public URL | Private DNS |
|---|---|---|---|
| Web (Next.js) | `tuev-smartcal-web` | https://tuev-smartcal-web.fly.dev | — |
| API (FastAPI) | `tuev-smartcal-api` | https://tuev-smartcal-api.fly.dev | `tuev-smartcal-api.internal` |
| DB (FalkorDB) | `tuev-smartcal-db` | — (internal only) | `tuev-smartcal-db.internal:6379` |

Frontend woła backend **przez publiczny HTTPS** (nie flycast — patrz sekcja "Dlaczego nie flycast" niżej). Użytkownik nigdy nie dzwoni do backendu bezpośrednio — tylko `/api/*` na web origin, gdzie Route Handler `app/api/[...path]/route.ts` proxyuje do `API_UPSTREAM`.

## Ruch docelowy

```
user → https://tuev-smartcal.synapseos.io/*        (public, custom domain)
          └─ frontend (tuev-smartcal-web)
                └─ /api/* → Route Handler proxy → https://tuev-smartcal-api.fly.dev
                                                     └─ FalkorDB via tuev-smartcal-db.internal:6379
```

## Custom domain — `tuev-smartcal.synapseos.io`

Cert już utworzony (`fly certs create` wykonane). Wait for DNS propagation, then Let's Encrypt auto-issues.

### GoDaddy DNS (zalogowana domena synapseos.io)

1. GoDaddy → **My Products** → **synapseos.io** → **DNS**
2. **Add New Record**:
   - Type: **CNAME**
   - Name: **tuev-smartcal**
   - Value: **tuev-smartcal-web.fly.dev**
   - TTL: **1 Hour** (default)
3. Save

Alternative (jeśli GoDaddy wymusi A/AAAA zamiast CNAME dla subdomeny):
- Type A,  Name `tuev-smartcal`, Value `66.241.125.137`
- Type AAAA, Name `tuev-smartcal`, Value `2a09:8280:1::108:2ee1:0`

### Weryfikacja

```bash
fly certs check tuev-smartcal.synapseos.io -a tuev-smartcal-web
# Status: pending (DNS) → awaiting certificate → active

dig tuev-smartcal.synapseos.io +short
curl -I https://tuev-smartcal.synapseos.io/api/health
```

Po aktywacji: `https://tuev-smartcal.synapseos.io/blitzschutz` = demo.

## Graph bootstrap (już wykonane)

- `POST /api/graph/load` → załadowane `smartcal` (154/183)
- `fly ssh console -a tuev-smartcal-api -C "python -c 'from products.blitzschutz.graph_schema import load_blitzschutz_graph; load_blitzschutz_graph()'"` → `blitzschutz` (73/18)

Jeśli kiedyś FalkorDB zostanie zresetowana (np. nowy volume), trzeba to powtórzyć.

## Secrets

- `tuev-smartcal-api`: `ANTHROPIC_API_KEY`, `SMARTCAL_API_KEY`
- `tuev-smartcal-web`: `SMARTCAL_API_KEY` (shared z API)

## User-facing login

Custom login page (`frontend/components/LoginScreen.tsx`) — "Synapse OS for TÜV Süd". Renderowany przez `app/page.tsx` na root (`/`) dopóki user się nie zaloguje.

**Obecne creds:** `tuev` / `TuevSmartcal2026##!` (share z TÜV team).

Zmiana hasła — edytuj linię 16 `LoginScreen.tsx` i redeploy:
```bash
cd frontend && fly deploy --ha=false
```

Uwaga: login jest client-side (useState, nie server). Chroni przed przypadkowym odkryciem URL przez zewnętrznych — **nie** przed technicznym inwestygatorem (bypass w DevTools).

## Auth

Backend wymaga `X-API-Key: $SMARTCAL_API_KEY` na każdy `/api/*`. Brak klucza / zły klucz → **401**.
Web Route Handler (`app/api/[...path]/route.ts`) wstrzykuje klucz server-side — przeglądarka nigdy go nie widzi.
Weryfikacja przez `hmac.compare_digest` (constant-time).

Bez `SMARTCAL_API_KEY` w env backend **odmawia startu** (safe-fail, `RuntimeError`).

### Rotacja klucza

```bash
NEW=$(openssl rand -hex 32)
fly secrets set SMARTCAL_API_KEY="$NEW" -a tuev-smartcal-api --stage
fly secrets set SMARTCAL_API_KEY="$NEW" -a tuev-smartcal-web --stage
# Deploy web FIRST (wysyła nowy header, API jeszcze stary akceptuje)
cd frontend && fly deploy --ha=false
# Potem API (przestaje akceptować stary)
cd ../backend && fly deploy --ha=false
```

Sub-sekundowe okno 401 w trakcie rotacji (aktywne sesje dostaną jeden odrzut, retry się uda).

## Dlaczego nie flycast (internal networking)

Próbowaliśmy dwie wersje internal DNS — obie nie działały czysto:

- **`.internal`** — Node.js `fetch` nie obsługuje `.internal` DNS (only resolver, no AAAA in default lookup) → `ENOTFOUND`.
- **`.flycast`** — kompilowany `force_https=true` na backendzie wymusza TLS handshake nawet dla private-ingress, a internal cert nie matchuje hostname `.flycast` → `ECONNRESET`.

Obejście `force_https=false` lub `[[services]]` bez HTTPS łamie public HTTPS, którego potrzebujemy dla dem poza TÜV network.

**Decyzja:** Route Handler proxy → publiczny HTTPS URL backendu. Koszt: backend jest wystawiony pod `tuev-smartcal-api.fly.dev`. Dla Phase 2 dodać HTTP Basic Auth / shared secret header żeby tylko frontend mógł wołać (nie real user).

## Koszt miesięczny (obecna konfiguracja)

- `tuev-smartcal-web`: shared-cpu-1x 512MB, auto-stop, min 1 → ~$3/mc
- `tuev-smartcal-api`: shared-cpu-1x 1GB, suspend, **min 1** (demo stability) → ~$5/mc
- `tuev-smartcal-db`: shared-cpu-1x 1GB, always-on, 3GB volume → ~$6/mc
- **Total: ~$14/mc**

## Redeploy

Po zmianach w kodzie:

```bash
# API
cd backend && fly deploy --ha=false

# Web
cd frontend && fly deploy --ha=false

# DB (rzadko — tylko przy zmianie image/config)
cd infra/falkordb && fly deploy --ha=false
```

## Troubleshooting

- **`/api/*` zwraca 500 via web** → `fly logs -a tuev-smartcal-web` — sprawdź czy fetch się nie dusi na TLS/DNS.
- **`FalkorDB connected` nie pojawia się w logach API** → `fly status -a tuev-smartcal-db`, `fly ssh console -a tuev-smartcal-api -C "python -c 'from database import get_graph; print(get_graph())'"`
- **SSE nie strumieniuje** → Route Handler ma `duplex: "half"` i forwarduje `upstream.body` jako stream — sprawdź czy upstream też nie bufuje (uvicorn domyślnie tak, ale sse-starlette ustawia `Transfer-Encoding: chunked`).
- **Hildesheim (lub inne miasto) ma Reisekosten 0** → sprawdź czy Nominatim osiągalny z maszyny API: `fly ssh console -a tuev-smartcal-api -C "python -c 'from common.geocode import geocode; print(geocode(\"Hildesheim\"))'"`

## Backupy FalkorDB

Fly robi **daily snapshots volume'u** (5-dniowa retencja). Przywrócenie: `fly volumes list -a tuev-smartcal-db` → znajdź snapshot → `fly volumes fork <snapshot-id>` → zrestartować app na nowym volume.
