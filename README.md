# NOVA AI 1.6 Cloud

Assistente AI con interfaccia mobile-first, sfera viola, chat cloud e supporto vocale.

## Servizi
- Frontend: https://nova-ai-alpha-ochre.vercel.app (Vercel, root `frontend`)
- Backend: https://nova-ai-backend-f2gk.onrender.com (Render, regione Frankfurt)
- Repository: https://github.com/rdavide2011-ai/NOVA-AI
- I push sul ramo `main` attivano il deploy automatico su Vercel e Render.

## Configurazione richiesta
La chat AI usa Gemini. Configurare `GEMINI_API_KEY` **solo nelle variabili d'ambiente di Render**, mai in GitHub o nel browser. Senza questa variabile, l'endpoint `/api/chat` restituisce 503.

L'origine CORS autorizzata su Render è `https://nova-ai-rdavide2011-ais-projects.vercel.app`. Se si utilizza un dominio differente, aggiornare `ALLOWED_ORIGINS` in Render.

## Avvio locale
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

Per eseguire il frontend localmente, configurare `frontend/config.js` e servirlo con un web server locale. Non inserire credenziali segrete nel frontend.

## Voce
Nel cloud gratuito il backend è configurato con `ENABLE_KOKORO=false`: la voce usata è quella sintetica italiana disponibile nel browser/dispositivo. Non è la voce Nicola. Il backend include comunque l'integrazione opzionale Kokoro: richiede memoria e risorse adeguate, `requirements-voice.txt` e `ENABLE_KOKORO=true`.

## Avvertenze
- Render gratuito può sospendere il servizio inattivo e rallentare la prima richiesta.
- Senza login l'API chatbot è pubblica: prima di finanziare un'API a consumo, aggiungere autenticazione, limiti e controllo quote. Il rate-limit applicativo è solo una protezione minimale.
- Il riconoscimento vocale dipende dal browser e non è garantito su tutti i dispositivi.
- Dynamic Island sul sito è una simulazione, non la Live Activity nativa di iOS.
- Non caricare mai file `.env`, password, token o chiavi API nel repository.
