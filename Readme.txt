# TeleMastodon
Questo progetto è un bot per pubblicare l'immagine delle ultime notizie dal servizio Televideo italiano su Mastodon.

## File

- **Autenticazione.py**: Gestisce il processo di autenticazione per la creazione dell'app Mastodon (da eseguire una sola volta).
- **Creazione.py**: Crea un'applicazione Mastodon e salva le credenziali del client (da eseguire una sola volta).
- **Telemastodon.py**: Script principale del bot che controlla il feed RSS di Televideo e l'immagine delle ultime notizie, e pubblica aggiornamenti su Mastodon.

## Configurazione

1. Esegui `Autenticazione.py` per autenticarti con Mastodon e salvare le credenziali dell'utente.
2. Esegui `Creazione.py` per creare l'applicazione Mastodon e salvare le credenziali del client.
3. Esegui `Telemastodon.py` per avviare il bot.

## Requisiti

- Python 3.11
- Mastodon.py
- Requests
- Feedparser
- Pillow

## Utilizzo

1. Assicurati di avere installato i pacchetti Python richiesti.
2. Segui le istruzioni di configurazione per autenticarti con Mastodon.
3. Esegui lo script principale del bot per iniziare a pubblicare aggiornamenti su Mastodon.