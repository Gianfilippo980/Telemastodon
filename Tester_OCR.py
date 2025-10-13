"""Programma per verificare il funzionamento dell'OCR sul televideo"""

import pytesseract
from PIL import Image
import time
import requests
from io import BytesIO
import re

indirizzo_immagine: str = ("https://www.televideo.rai.it/televideo/pub/tt4web/"
                           "Nazionale/16_9_page-101.png")


def scarica_immagine(indirizzo: str = indirizzo_immagine) -> Image.Image | None:
    try:
        risposta = requests.get(indirizzo)
        risposta.raise_for_status()
        immagine = Image.open(BytesIO(risposta.content))
        return immagine
    except ConnectionError():
        print("Errore connessione")
        return None


def riconosci_testo(zona_orario: Image.Image) -> str:
    # Converto in Grigio
    zona_orario = zona_orario.convert("L")
    # Converto in Binario
    zona_orario = zona_orario.point(lambda p: 255 if p > 127 else 0)
    testo = pytesseract.image_to_string(zona_orario, lang='ita',
                                        config='--psm 7')
    testo = re.sub(r'[^0-9.]', '', testo)
    return testo


def orario(testo: str) -> time.struct_time | None:
    # try:
    ora = time.strptime(testo, "%H.%M")
    return ora
#    except:
#        print("Errore orario")
#        return None


def main() -> None:
    testo = ''
    while True:
        immagine = scarica_immagine(indirizzo_immagine)
        if immagine is not None:
            # Ritaglio
            zona_orario = immagine.crop((24, 28, 119, 53))
            nuovo_testo = riconosci_testo(zona_orario)
            ora_vera = (str(time.localtime().tm_hour) + ':'
                        + str(time.localtime().tm_min))
            if nuovo_testo != testo:
                print(ora_vera, '->', nuovo_testo)
                testo = nuovo_testo
                if int(testo[:2]) != int(ora_vera[:2]):
                    zona_orario.save((ora_vera + '.png'))
        time.sleep(20)


if __name__ == '__main__':
    main()
