# frontend/ — MedRoBERTa PII Shield (UI)

React + Vite + TypeScript single-page app for the interactive demo. Users type
Dutch clinical text or drop a file, and the app shows the **masked** result — for
PDFs it returns a **downloadable masked PDF** with the original layout preserved.

It talks to the **redaction demo API** ([`backend/main.py`](../backend/main.py)):

| Action | Request | Response |
|---|---|---|
| Type text | `POST http://localhost:8000/api/chat` `{text}` | `{redacted_text}` |
| Upload file | `POST http://localhost:8000/api/upload` (multipart) | masked text, **or** `application/pdf` for PDF input |

## Run

```bash
npm install
npm run dev        # http://localhost:5173  (expects the demo API on :8000)
```

The demo API must be running (`python backend/main.py`). The one-click
[`start_chatbot.bat`](../start_chatbot.bat) launches both.

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Type-check (`tsc -b`) + production build to `dist/` |
| `npm run preview` | Serve the production build locally |

## Notes

- The backend base URL (`http://localhost:8000`) is set in
  [`src/App.tsx`](src/App.tsx); change it for a non-local deployment.
- Stack: React 19, Vite, TypeScript, Oxlint.
- No PII is stored client-side; files are sent to the demo API and the masked
  result is shown / offered as a download.
