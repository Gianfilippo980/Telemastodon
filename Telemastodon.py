"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del
Televideo RAI"""
# Questa versine del bot usa l'OCR per riconosce l'ora dell'immagine e la
# confronta con l'ora dell'ultima notizia RSS, se le due ore coincidono entro
# una finestra, il bot posta l'immagine e il sommario della notizia

import time
from io import BytesIO

import requests
import feedparser
from PIL import Image
import pytesseract
from mastodon import Mastodon


# Costanti
INDIRIZZO_IMMAGINE = ("https://www.televideo.rai.it/televideo/pub/tt4web/"
                      "Nazionale/16_9_page-101.png")
INDIRIZZO_FEED = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'
HASHTAG = "#Televideo #Ultimora #Italy"
SLEEP = 20
FINESTRA = 10
# Finestra è il numero di minuti di differenza fra gli orarî dell'immagine e
# del feed entro cui sono ritenuti contemporanei.


# Definisco le classi
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
        e restituisce la nuova ora, altrimenti restituisce None
        """
        try:
            nuovo_lancio = feedparser.parse(self.indirizzo).entries[0]
        except Exception as errore:
            # La libreria sta cambiando nome alle sue eccezioni.
            print("Errore RSS!", errore)
            return None
        if (hasattr(nuovo_lancio, 'title')
                and hasattr(nuovo_lancio, 'summary')
                and hasattr(nuovo_lancio, 'published_parsed')):
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
        forma di <a href="...">...</a>
        """
        while "<a" in testo:
            inizio = testo.find("<a")
            fine = testo.find(">", inizio)
            testo = testo[:inizio] + testo[fine + 1:]
            inizio = testo.find("</a>")
            testo = testo[:inizio] + ' ' + testo[inizio + 4:]
        return testo

    def titolo(self, hashtag: str) -> str | None:
        """Restituisce il titolo dell'ultimo lancio RSS scaricato, a cui
        aggiunge due righe binache e gli hashtag
        """
        if self.lancio is not None and isinstance(self.lancio.title, str):
            return self.lancio.title + "\n\n" + hashtag
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
        quel valore
        """
        stato = self.flag_nuovo
        if imposta is not None:
            self.flag_nuovo = imposta
        return stato


class Immagine:
    """Gestione dell'immagine da web, ogni isatanza corrisponde
    ad un solo URL.
    """
    def __init__(self, indirizzo: str) -> None:
        self.indirizzo = indirizzo
        self.ora = time.localtime()
        self.immagine: Image.Image | None = None
        self.flag_nuovo = False
        self.testo_ocr = ""

    def scarica_immagine(self) -> Image.Image | None:
        """Scarica l'immagine, la salva nell'oggetto e la restituisce,
        restituisce None se fallisce.
        """
        try:
            risposta = requests.get(self.indirizzo, timeout=60)
            risposta.raise_for_status()
        except requests.exceptions.RequestException as errore:
            print("Errore connessione!", errore)
            return None
        try:
            nuova_immagine = Image.open(BytesIO(risposta.content))
        except Exception as errore:
            print("Errore immagine!", errore)
            return None
        return nuova_immagine

    def aggiorna(self) -> time.struct_time | None:
        """Se l'ora tratta dall'ultima immaine è magiore della precedente,
        aggiorna l'oggetto, abilita la flag 'nuovo, aggiorna l'ora savata
        e restituisce la nuova ora, altrimenti restituisce None
        """
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
        formato time.struct_time, altrimenti restituisce None
        """
        if nuova_immagine is not None:
            zona_orario = nuova_immagine.crop((24, 28, 116, 53))
            # Ritaglio l'angolo in alto a sinistra.
            zona_orario = zona_orario.convert("L")
            # Converto in grigio
            zona_orario = zona_orario.point(lambda p: 255 if p > 100 else 0)
            # Converto in binario
            testo = pytesseract.image_to_string(
                zona_orario,
                lang='ita',
                config="--psm 7 -c tessedit_char_whitelist=0123456789.")
            # Per debug:
            if testo != self.testo_ocr:
                print("Testo OCR: ", testo)
                self.testo_ocr = testo
            if testo[0] == ".":
                # A volte lo 0 iniziale non viene riconosciuto
                testo = "0" + testo
            testo = testo.split('.')
            if len(testo) == 2:
                if len(testo[1]) > 2:
                    # Ci ouò essere uno 0 o un '\n' finale non voluto nei
                    # minuti, se ci sono 3 cifre tolgo l'ultima.
                    testo[1] = testo[1][:-1]
                ore, minuti = map(int, testo)
                oggi = time.localtime()
                try:
                    ora = time.struct_time((
                        oggi.tm_year,   # Anno
                        oggi.tm_mon,    # Mese
                        oggi.tm_mday,   # Giorno
                        ore,            # Ore
                        minuti,         # Minuti
                        0,              # Secondi (impostato a 0)
                        oggi.tm_wday,   # Giorno della settimana
                        oggi.tm_yday,   # Giorno dell'anno
                        oggi.tm_isdst   # Flag ora legale
                        ))
                    return ora
                except ValueError:
                    print("Errore formato orario")
        return None

    def nuovo(self, imposta: bool | None = None) -> bool:
        """Restituisce la flag di novità del feed, così com'è alla chiamata,
        se viene inserito il parametro imposta, la flag viene impostata su
        quel valore
        """
        stato = self.flag_nuovo
        if imposta is not None:
            self.flag_nuovo = imposta
        return stato

    def orario(self) -> time.struct_time | None:
        """Restituisce l'salvato, o None se l'immagine non è disponibile."""
        if self.immagine is not None:
            return self.ora
        return None

    def foto(self) -> Image.Image | None:
        """Restituisce l'immagine salvata nell'ogetto, se è presente."""
        return self.immagine


def posta_immagine(foto: Image.Image,
                   testo_post: str,
                   descrizione: str) -> None:
    """Pubblica un toot su Mastodon con il titolo, la foto
    e la descrizione dati.
    """
    buffer = BytesIO()
    foto.save(buffer, format='PNG')
    media = mastodon.media_post(buffer.getvalue(),
                                mime_type='image/png',
                                description=descrizione)
    mastodon.status_post(testo_post, media_ids=media, language='IT')


# Istanzio gli oggetti
mastodon = Mastodon(access_token='mstdn_access.secret')
rss = RSS(INDIRIZZO_FEED)
immagine = Immagine(INDIRIZZO_IMMAGINE)

while True:
    rss.aggiorna()
    immagine.aggiorna()
    # Verifica novità
    if rss.nuovo() and immagine.nuovo():
        ora_rss = rss.orario()
        ora_immaigne = immagine.orario()
        titolo_rss = rss.titolo(HASHTAG)
        descrizione_rss = rss.descrizione()
        immagine_disponibile = immagine.foto()
        # Verifica correttezza
        if (ora_rss is not None and ora_immaigne is not None
                and titolo_rss is not None and descrizione_rss is not None
                and immagine_disponibile is not None):
            # Verifica Compatibilità
            if (abs(time.mktime(ora_rss) - time.mktime(ora_immaigne))
                    < FINESTRA*60):
                print("Posto\n")
                posta_immagine(immagine_disponibile,
                               titolo_rss,
                               descrizione_rss)
                rss.nuovo(False)
                immagine.nuovo(False)
    time.sleep(SLEEP)
