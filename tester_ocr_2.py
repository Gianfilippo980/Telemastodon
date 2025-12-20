"""Stampa il risultato dell'OCR"""

from io import BytesIO
import time
import requests
from PIL import Image
import pytesseract

INDIRIZZO_IMMAGINE = ("https://www.televideo.rai.it/televideo/pub/tt4web/"
                      "Nazionale/16_9_page-101.png")
SLEEP = 20


class Immagine:
    """Gestione dell'immagine da web, ogni isatanza corrisponde
    ad un solo URL.
    """
    def __init__(self, indirizzo: str) -> None:
        self.indirizzo = indirizzo
        self.ora = time.localtime()
        self.immagine: Image.Image | None = None
        self.flag_nuovo = False

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
            print("ora immagine:", nuova_ora)
            if nuova_ora is not None and nuova_ora > self.ora:
                self.immagine = nuova_immagine
                self.ora = nuova_ora
                self.flag_nuovo = True
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


immagine = Immagine(INDIRIZZO_IMMAGINE)

while True:
    print(immagine.aggiorna(), "\n")
    time.sleep(SLEEP)
