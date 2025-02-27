"""Programma per verificare il funzionamento dell'OCR sul televideo"""

import pytesseract
from PIL import Image
import time
import requests
from io import BytesIO
import re

indirizzo_immagine = 'https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-101.png'

def scarica_immagine(indirizzo : str) -> Image.Image | None:
    try:
        risposta = requests.get(indirizzo)
        risposta.raise_for_status()
        immagine = Image.open(BytesIO(risposta.content))
        return immagine
    except:
        print("Errore immagine")
        return None
    
def riconosci_testo(immagine : Image.Image) -> str:
    zona_orario = immagine.crop((22, 24, 121, 55))
    testo = pytesseract.image_to_string(zona_orario, config='--psm 7')
    testo = re.sub(r'[^0-9.]', '', testo)
    return testo

def orario(testo: str) -> time.struct_time | None:
    try:
        ora = time.strptime(testo, "%H.%M")
        return ora
    except:
        print("Errore orario")
        return None
    
def main() -> None:
    testo = ''
    ora = None
    while True:
        immagine = scarica_immagine(indirizzo_immagine)
        if immagine is not None:
            nuovo_testo = riconosci_testo(immagine)
            ora_vera = str(time.localtime().tm_hour) + ':' + str(time.localtime().tm_min)
            if nuovo_testo != testo:
                print(ora_vera, '->', nuovo_testo)
                testo = nuovo_testo
        time.sleep(20)
        
if __name__ == '__main__':
    main()