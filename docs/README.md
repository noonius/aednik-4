# Aednik 4 veebirakendus

419 kirjet olemasolevast taimed.csv failist. Veebitööriist sisaldab pilt → nimed, eesti → ladina ja ladina → eesti harjutusi ning otsitavat õpinimekirja.

Õpiedu salvestub brauserisse. Offline-nupp salvestab rakenduse ja kõik pildid seadmesse. Telefonis lisa veebileht avakuvale; allalaadimise ajal hoia leht avatuna. Õpiedu saab JSON-failina eksportida ja importida. Import liidab uuemad vastused olemasoleva õpieduga.

Viimati valitud kategooria ja harjutussuund taastuvad lehe avamisel. Sessioon näitab hinnatud kaartide arvu ning ootel korduskaarte. „Võta viimane hinnang tagasi” taastab viimase kaardi, selle eelmise kordamisaja ja sessiooni seisu; tagasivõtmine kehtib praeguses sessioonis kuni järgmise hindamiseni. Küsimusele ja avatud vastusele liigub klaviatuurifookus, et sisu oleks ekraanilugejale kättesaadav. Kohalik fail ja veebiversioon kuvavad erinevaid offline-juhiseid.

Õpinimekirjas on iga kirje juures valitud harjutuse õppeskoor 0–6. See on olemasoleva kordamisalgoritmi tase: järjestikune „Teadsin” tõstab seda ja „Harjutan veel” nullib. Nimekirja keskmine arvestab otsingu tulemuste kõiki selle harjutuse kaarte, kaasa arvatud õppimata kaarte. Skoor ei ole meenutamise tõenäosus. Puuduva pildi või nime tõttu harjutuseks sobimatule kirjele skoori ei näidata.

Mobiilis on „Näita vastust”, hindamisnupud või sessiooni lõpus „Harjuta edasi” püsivalt ekraani alaservas. Harjutuse ja kategooria valikud asuvad õppimiskaardi järel. Nupuvajutused ei keri lehte automaatselt. Sisu all on nupuriba ning telefoni turvaala jaoks varuruum.

## Kohalik kasutamine

Ava juurkausta fail „Aednik 4.html” brauseris. See sisaldab pilte ja kogu rakendust ning töötab ilma võrguühenduseta. Ühe faili saab uuesti luua käsuga `.venv/bin/python build_standalone.py`.

Veebiversiooni jaoks käivita docs kaustast `python3 -m http.server 8000`. Teenuseworker töötab HTTPS-is või localhost-is. Telefoni iseseisvaks offline-kasutuseks on mõeldud avaldatud HTTPS-leht. GitHub Pagesi seadistamine on kirjeldatud [repositooriumi juhendis](../README.md).

## Materjali uuendamine

Käivita projekti juurkaustast `.venv/bin/python build_data.py`. Nimed tulevad CSV-st. Pildid ja nende omistused tulevad värskest Anki pakist. Fotode omistused säilivad vastuse juures.

## Kontroll

Käivita `node test_study.cjs`. Test kontrollib andmete terviklikkust, harjutuse ja rühma filtreid, ajastamist, õpiedu impordi valideerimist ning offline-failide olemasolu.

## Piirangud

Õpiedu ei sünkrooni automaatselt seadmete ega Ankiga. Ajastamine kasutab lihtsaid intervalle, mitte FSRS-i. 52 kirjel puudub pilt ning 47 kirjel ladinakeelne nimi; need jäävad õpinimekirjas nähtavaks. Brauseriandmete kustutamine eemaldab kohaliku õpiedu ja offline-materjali.
