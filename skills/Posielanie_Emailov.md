# Posielanie Emailov

## Metaúdaje
- **Názov**: Posielanie Emailov
- **Verzia**: 1.0
- **Autor**: Twin AI
- **Dátum**: 2026-03-22

## Popis
Tento skill umožňuje asistentovi poslať email na zadanú adresu s daným predmetom a obsahom.

## Parametre
- `adresa`: E-mailová adresa príjemcu.
- `predmet`: Predmet e-mailu.
- `obsah`: Obsah e-mailu.

## Príklad použitia
```python
# Poslanie emailu na adresu example@example.com s predmetom "Test" a obsahom "Ahoj, toto je testovací email."
vysledok = posli_email(adresa="example@example.com", predmet="Test", obsah="Ahoj, toto je testovací email.")
```

## Implementácia
```python
import smtplib
from email.message import EmailMessage

def posli_email(adresa: str, predmet: str, obsah: str) -> str:
    """
    Funkcia na poslanie emailu na zadanú adresu s daným predmetom a obsahom.
    
    Parametre:
        adresa (str): E-mailová adresa príjemcu.
        predmet (str): Predmet e-mailu.
        obsah (str): Obsah e-mailu.
        
    Navrát:
        str: Správa o úspešnom odoslaní alebo chybe.
    """
    try:
        # Nastavenie SMTP servera a prihlasovacích údajov
        server = smtplib.SMTP('smtp.example.com', 587)
        server.starttls()
        server.login("vas_email@example.com", "vas_heslo")
        
        # Vytvorenie e-mailu
        email = EmailMessage()
        email['From'] = "vas_email@example.com"
        email['To'] = adresa
        email['Subject'] = predmet
        email.set_content(obsah)
        
        # Odoslanie e-mailu
        server.send_message(email)
        server.quit()
        
        return "Email bol úspešne odoslaný."
    except Exception as e:
        return f"Chyba pri odosielaní emailu: {str(e)}"
```

## Poznámky
- Uistite sa, že nahradíte `"smtp.example.com"`, `"vas_email@example.com"` a `"vas_heslo"` svojimi skutočnými SMTP serverom a prihlasovacími údajmi.
- Tento skill používa štandardnú knižnicu `smtplib` pre posielanie e-mailov. Uistite sa, že máte prístup k SMTP serveru s povoleným odosielaním e-mailov zo vašej aplikácie.
- Ak je potrebné poslať email s HTML obsahom, môžete použiť `email.set_content(obsah, subtype='html')` namiesto `email.set_content(obsah)`.