"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del
Televideo RAI"""
# Questa versine del bot usa l'OCR per riconosce l'ora dell'immagine e la
# confronta con l'ora dell'ultima notizia RSS, se le due ore coincidono entro
# una finestra, il bot posta l'immagine e il sommario della notizia

import re
import time
from io import BytesIO

import requests
import feedparser
from PIL import Image
import pytesseract
from mastodon import Mastodon


# Indirizzi
INDIRIZZO_IMMAGINE = """https://www.televideo.rai.it/televideo/pub/tt4web/
    Nazionale/16_9_page-101.png"""
INDIRIZZO_FEED = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'

# Periodi temporali, la finestra è il numero di minuti di differenza fra gli
# orarî dell'immagine e del feed entro cui sono ritenuti contemporanei.
SLEEP = 20
FINESTRA = 10


class RSS:
    """Gestione feed RSS, ogni istanza corrisponde ad un solo URL."""
    def __init__(self, indirizzo: str) -> None:
        self.indirizzo = indirizzo
        self.ora = time.localtime()
        self.lancio = None
        self.flag_nuovo = False

    def aggiorna(self) -> time.struct_time | None:
        """Se l'ora dell'ultima notizia è magiore della precedente, aggiorna
        l'oggetto, abilita la flag 'nuovo, aggiorna l'ora savata
        e restituisce la nuova ora, altrimenti restituisce None"""
        try:
            nuovo_lancio = feedparser.parse(self.indirizzo).entries[0]
        except Exception as errore:
            # La libreria sta cambiando nome alle sue eccezioni.
            print("Errore RSS!", errore)
            return None
        if ('published_parsed', 'title', 'summary') in nuovo_lancio:
            # I lanci che non contengono questi elementi sono inutili.
            ora_lancio = time.localtime(
                time.mktime(nuovo_lancio.published_parsed) + 3_600)
            # Aggiunge un'ora per il fuso orario
            if ora_lancio > self.ora:
                # Il nuovo lancio è successivo all'ultimo acquisito
                self.ora = ora_lancio
                self.lancio = nuovo_lancio
                self.flag_nuovo = True
                print("ora rss: ", ora_lancio)
                return self.ora
        return None

    def __filtra_link(self, testo: str) -> str:
        """Rimuove i link dal testo, alle volte presenti nel sommario sotto la
        forma di <a href="...">...</a>"""
        while "<a" in testo:
            inizio = testo.find("<a")
            fine = testo.find(">", inizio)
            testo = testo[:inizio] + testo[fine + 1:]
            inizio = testo.find("</a>")
            testo = testo[:inizio] + ' ' + testo[inizio + 4:]
        return testo

    def titolo(self) -> str | None:
        """Restituisce il titolo dell'ultimo lancio RSS scaricato"""
        if self.lancio is not None and isinstance(self.lancio.title, str):
            return self.lancio.title + "\n\n" + "#Televideo #Ultimora"
        return None

    def descrizione(self) -> str | None:
        """Restituisce il sommario dell'ultimo lancio RSS scaricato"""
        if self.lancio is not None and isinstance(self.lancio.summary, str):
            testo = self.__filtra_link(self.lancio.summary)
            return testo
        return None

    def orario(self) -> time.struct_time | None:
        """Restituisce l'orario del lancio, o None se non è disponibile."""
        if self.lancio is not None:
            return self.ora
        return None

    def nuovo(self, imposta: bool | None = None) -> bool:
        """Restituisce la flag di novità del feed, così com'è alla chiamata,
        se viene inserito il parametro imposta, la flag viene impostata su
        quel valore"""
        stato = self.flag_nuovo
        if imposta is not None:
            self.flag_nuovo = imposta
        return stato


class Immagine:
    """Gestione dell'immagine da web, ogni isatanza corrisponde
    ad un solo URL."""
    def __init__(self, indirizzo: str) -> None:
        self.indirizzo = indirizzo
        self.ora = time.localtime()
        self.immagine: Image.Image | None = None
        self.flag_nuovo = False

    def scarica_immagine(self) -> Image.Image | None:
        """Scarica l'immagine, la salva nell'oggetto e la restituisce,
        restituisce None se fallisce."""
        try:
            risposta = requests.get(self.indirizzo, timeout=60)
            risposta.raise_for_status()
        except requests.exceptions.RequestException as errore:
            print("Errore connessione", errore)
            return None
        try:
            nuova_immagine = Image.open(BytesIO(risposta.content))
        except Exception as errore:
            print("Errore immagine!", errore)
            return None
        self.immagine = nuova_immagine
        return nuova_immagine

    def aggiorna(self) -> time.struct_time | None:
        """Se l'ora tratta dall'ultima immaine è magiore della precedente,
        aggiorna l'oggetto, abilita la flag 'nuovo, aggiorna l'ora savata
        e restituisce la nuova ora, altrimenti restituisce None"""
        nuova_immagine = self.scarica_immagine()
        if nuova_immagine is not None:
            nuova_ora = self.riconosci_orario(nuova_immagine)
            if nuova_ora is not None and nuova_ora > self.ora:
                self.immagine = nuova_immagine
                self.ora = nuova_ora
                self.flag_nuovo = True
                print("ora immagine:", nuova_ora)
                return nuova_ora
        return None

    def riconosci_orario(self, nuova_immagine: Image.Image
                         ) -> time.struct_time | None:
        """Analizza l'immagine che gli viene passata, effettua l'OCR
        nell'angolo superiore sinistro, se riesce, restituisce un orario in
        formato time.struct_time, altrimenti restituisce None"""
        if nuova_immagine is not None:
            zona_orario = nuova_immagine.crop((24, 28, 118, 53))
            # Ritaglio l'angolo in alto a sinistra.
            zona_orario = zona_orario.convert("L")
            # Converto in grigio
            zona_orario = zona_orario.point(lambda p: 255 if p > 100 else 0)
            # Converto in binario
            testo = pytesseract.image_to_string(zona_orario,
                                                lang='ita',
                                                config='--psm 7')
            testo = re.sub(r'[^0-9.]', '', testo)
            testo = testo.split('.')
            if len(testo) == 2:
                if len(testo[1]) > 2:
                    # Ci ouò essere uno 0 finale non voluto nei minuti, se ci
                    # sono 3 cifre tolgo l'ultima.
                    testo[1] = testo[1][:2]
                try:
                    ora = time.strptime(testo, "%H.%M")
                    return ora
                except ValueError:
                    print("Errore formato orario")
        return None

    def nuovo(self, imposta: bool | None = None) -> bool:
        """Restituisce la flag di novità del feed, così com'è alla chiamata,
        se viene inserito il parametro imposta, la flag viene impostata su
        quel valore"""
        stato = self.flag_nuovo
        if imposta is not None:
            self.flag_nuovo = imposta
        return stato

    def orario(self) -> time.struct_time | None:
        """Restituisce l'salvato, o None se l'immagine non è disponibile."""
        if self.immagine is not None:
            return self.ora
        return None


def posta_immagine(foto, titolo, descrizione) -> None:
    """Pubblica un toot su Mastodon con il titolo, la foto
    e la descrizione dati."""
    buffer = BytesIO()
    foto.save(buffer, format='PNG')
    media = mastodon.media_post(buffer.getvalue(),
                                mime_type='image/png',
                                description=descrizione)
    mastodon.status_post(titolo, media_ids=media, language='IT')


mastodon = Mastodon(access_token='mstdn_access.secret')
rss = RSS(INDIRIZZO_FEED)
immagine = Immagine(INDIRIZZO_IMMAGINE)

while True:
    if (rss.nuovo() and immagine.nuovo() and
            rss.orario() is not None and immagine.orario() is not None):
        if (time.mktime(rss.orario()) - time.mktime(immagine.orario())
                < FINESTRA*60):
            print("Posto")
            posta_immagine(immagine.immagine, rss.titolo(), rss.descrizione())
            rss.nuovo(False)
            immagine.flag_nuovo = False
    time.sleep(SLEEP)
