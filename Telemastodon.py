"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del Televideo"""
#Questa versine del bot posta una nuova immagine solo se entrambi i feed sono stati aggiornati entro le rispettive finestre di tempo, per evitare di postare un'immagine vecchia con un titolo nuovo.

import re
import requests
import feedparser
import time
import threading
from PIL import Image
import pytesseract
from io import BytesIO
from mastodon import Mastodon
from Credenziali import mastodon as credenziali_mastodon


#Indirizzi
indirizzo_immagine = "https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-101.png"
indirizzo_feed = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'

#Periodi Temporali
#Gli sleep sono il tempo che passa fra due dowload dal web
sleep_rss = 20
sleep_immagine = 20
sleep_post = 10
#La finestra è la differenza di tempo enrto la quale immagine e notizia sono considerate contemporanee
finestra = 120

class RSS:
    def __init__(self, intervallo_controlli : int, indirizzo : str) -> None:
        self.indirizzo = indirizzo
        self.sleep = intervallo_controlli
        self.ora_ultima = time.localtime()
        self._stop = threading.Event()
        self.thread = threading.Thread(target= self._ciclo)
        self.thread.start()
        self.lancio = None
        self.nuovo = False

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.aggiorna()
            time.sleep(self.sleep)

    def aggiorna(self) -> None:
        try:
            nuovo_lancio = feedparser.parse(self.indirizzo).entries[0]
            #Aggiunge un'ora per il fuso orario
            ora_lancio = time.localtime(time.mktime(nuovo_lancio.published_parsed) + 3_600)
            if ora_lancio > self.ora_ultima:
                self.ora_ultima = ora_lancio
                self.lancio = nuovo_lancio
                self.nuovo = True
                print("ora rss:     ", ora_lancio)
        except:
            print("Errore RSS")

    def filtra_link(self, testo : str) -> str:
        #Rimuove i link dal testo, alle volte presenti nel sommario sotto la forma di <a href="...">...</a> e che di solito non portano da nessuna parte
        if "<a" in testo:
            inizio = testo.find("<a")
            fine = testo.find(">", inizio)
            testo = testo[:inizio] + testo[fine + 1:]
            inizio = testo.find("</a>")
            testo = testo[:inizio] + testo[inizio + 4:]
        return testo

    def titolo(self) -> str | None:
        #Restituisce il titolo dell'ultimo lancio RSS scaricato
        try:
            return self.lancio.title + "\n\n" + "#Televideo #Ultimora"
        except:
            return None 
        
    def descrizione(self) -> str | None:
        #Restituisce il sommario dell'ultimo lancio RSS scaricato
        try:
            testo = self.filtra_link(self.lancio.summary)
            return testo
        except:
            return None

class Immagine:
    def __init__(self, indirizzo : str, intervallo_controlli : int) -> None:
        self.indirizzo = indirizzo
        self.ora_immagine = time.localtime()
        self.intervallo = intervallo_controlli
        self._stop = threading.Event()
        self.thread = threading.Thread(target= self._ciclo)
        self.thread.start()
        self.immagine = None
        self.nuovo = False

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.aggiorna()
            time.sleep(self.intervallo)

    def scarica_immagine(self) -> Image.Image | None:
        try:
            risposta = requests.get(self.indirizzo)
            risposta.raise_for_status()
            immagine = Image.open(BytesIO(risposta.content))
            return immagine
        except:
            print("Errore immagine")
            return None
    
    def aggiorna(self) -> None:
        nuova_immagine = self.scarica_immagine()
        if nuova_immagine is not None:
            nuova_ora = self.riconosci_orario(nuova_immagine)
            if nuova_ora is not None and nuova_ora > self.ora_immagine:
                self.immagine = nuova_immagine
                time.sleep(1)
                self.ora_immagine = nuova_ora
                self.nuovo = True
                print("ora immagine:", nuova_ora)

    def riconosci_orario(self, immagine : Image) -> time.struct_time | None:
        if immagine is None:
            return None
        zona_orario = immagine.crop((22, 24, 121, 55))
        testo = pytesseract.image_to_string(zona_orario, config='--psm 7')
        # Validazione dei dati OCR
        testo = re.sub(r'[^0-9.]', '', testo)
        testo = testo.split('.')
        if len(testo) == 2:
            ora = float(testo[0])
            minuti = float(testo[1])
            if ora >0 and ora < 24 and minuti >= 0 and minuti < 60:
                data = ''
                for t in time.localtime()[:3]:
                    data += str(t) + '.'
                return time.strptime(data + testo[0] + '.' + testo[1], "%Y.%m.%d.%H.%M")
        return None

#Gestione Mastodon
mastodon = Mastodon(client_id = 'Telepython_client.secret')
mastodon.log_in(credenziali_mastodon.email, credenziali_mastodon.password, to_file= 'Telepython_utente.secret', scopes=['write'])

def posta_immagine(immagine, titolo, descrizione) -> None:
    bytes= BytesIO()
    immagine.save(bytes, format= 'PNG')
    media = mastodon.media_post(bytes.getvalue(), mime_type= 'image/png', description= descrizione)
    mastodon.status_post(titolo, media_ids= media, language= 'IT')

#Ciclo principale
rss = RSS(sleep_rss, indirizzo_feed)
immagine = Immagine(indirizzo_immagine, sleep_immagine)

while True:
    if rss.nuovo and immagine.nuovo and time.mktime(rss.ora_ultima) - time.mktime(immagine.ora_immagine) < finestra:
        print("Posto")
        posta_immagine(immagine.immagine, rss.titolo(), rss.descrizione())
        rss.nuovo = False
        immagine.nuovo = False
    time.sleep(sleep_post)