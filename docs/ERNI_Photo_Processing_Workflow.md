# Detaillierte Beschreibung des Arbeitsablaufs (Workflow) des Projekts

## Allgemeine Übersicht

Dieses Projekt stellt ein automatisiertes System zur Verarbeitung von Fotografien von Bauprojekten der Firma ERNI dar, die sich auf Holzstrukturen spezialisiert hat. Das System führt den vollständigen Verarbeitungszyklus durch: von der Hochladung von Fotografien aus SharePoint, ihrer Analyse mithilfe von künstlicher Intelligenz, bis hin zur Generierung von Metadaten und dem Hochladen zurück in SharePoint mit angereicherten Informationen.

## Detaillierter Arbeitsablauf

### 1. Initialisierung und Konfiguration

**Komponenten:**
- Docker-Container mit Python-Umgebung
- Konfigurationsdateien (config.env, sharepoint_choices.json)
- Verzeichnisse zur Datenspeicherung

**Prozess:**
1. Das System wird geladen und initialisiert die erforderlichen Verzeichnisse:
   - `/app/data/downloads` - für den Download von Dateien aus SharePoint
   - `/app/data/metadata` - zur Speicherung von EXIF-Metadaten
   - `/app/data/analysis` - für die Analyseergebnisse von OpenAI
   - `/app/data/upload` - zur Vorbereitung von Dateien für den Upload
   - `/app/data/uploaded` - für erfolgreich hochgeladene Dateien
   - `/app/data/processed` - für verarbeitete Dateien
   - `/app/data/registry` - für das Register der Dateien

2. Das System lädt die Konfiguration:
   - SharePoint-Anmeldeinformationen
   - Einstellungen für die OpenAI API
   - Prompts zur Analyse von Fotografien
   - Schema der SharePoint-Metadaten

### 2. Hochladen des Metadatenschemas aus SharePoint

**Modul:** `metadata_schema.py`

**Prozess:**
1. Das System verbindet sich mit SharePoint unter Verwendung der Anmeldeinformationen
2. Extrahiert das Metadatenschema aus der Bibliothek "Referenzfotos"
3. Wandelt das Schema in ein benutzerfreundliches Format um
4. Speichert das Schema in der Datei `sharepoint_choices.json`

**Ergebnis:**
- Datei mit dem vollständigen Metadatenschema, einschließlich:
  - Feldnamen
  - Feldtypen (Text, Auswahl, Mehrfachauswahl)
  - Zulässige Werte für Auswahlfelder
  - Pflichtfelder

### 3. Hochladen von Fotografien aus SharePoint

**Modul:** `photo_metadata.py`

**Prozess:**
1. Das System verbindet sich mit SharePoint
2. Holen Sie sich eine Liste von Fotografien aus der Bibliothek "Referenzfotos"
3. Lädt Fotografien in Paketen von 10 Stück hoch
4. Für jede Fotografie:
   - Überprüft die Dateigröße (überspringt Dateien > 15 MB)
   - Lädt die Datei in das Verzeichnis `/app/data/downloads`
   - Extrahiert EXIF-Metadaten mithilfe der PIL-Bibliothek
   - Formatiert die EXIF-Daten in ein lesbares Format, einschließlich GPS-Koordinaten
   - Speichert die Metadaten in einer YAML-Datei im Verzeichnis `/app/data/metadata`
   - Fügt einen Eintrag in das Register der hochgeladenen Dateien hinzu
   - Verschiebt die Datei in das Verzeichnis `/app/data/processed` auf der SharePoint-Seite

**Ergebnis:**
- Hochgeladene Fotografien im Verzeichnis `/app/data/downloads`
- YAML-Dateien mit EXIF-Metadaten im Verzeichnis `/app/data/metadata`
- Aktualisiertes Register der hochgeladenen Dateien

### 4. Analyse von Fotografien mit OpenAI

**Modul:** `openai_analyzer.py`

**Prozess:**
1. Das System findet Fotografien im Verzeichnis `/app/data/downloads`
2. Lädt das Metadatenschema aus der Datei `sharepoint_choices.json`
3. Lädt den ausgewählten Prompt-Typ aus der entsprechenden Datei in `/app/config/prompts/`
4. Für jede Fotografie:
   - Überprüft, ob sie bereits analysiert wurde (nach Dateihash)
   - Extrahiert und formatiert die EXIF-Metadaten
   - Bereitet den Prompt für OpenAI vor, einschließlich der EXIF-Daten
   - Optimiert das Bild (reduziert auf eine maximale Größe von 1024 Pixel)
   - Kodiert das Bild in base64
   - Sendet eine Anfrage an die OpenAI API (Modell GPT-4o)
   - Erhält und analysiert die JSON-Antwort
   - Speichert die Analyseergebnisse in einer JSON-Datei im Verzeichnis `/app/data/analysis`
   - Fügt einen Eintrag in das Register der analysierten Dateien hinzu

**Besonderheiten:**
- Parallelverarbeitung mit ThreadPoolExecutor
- Begrenzung der gleichzeitigen Anfragen (OPENAI_CONCURRENCY_LIMIT = 10)
- Mechanismus für Wiederholungsversuche bei Fehlern
- Caching der Analyseergebnisse
- Verschiedene Prompt-Typen für unterschiedliche Analyseanforderungen

**Ergebnis:**
- JSON-Dateien mit Analyseergebnissen im Verzeichnis `/app/data/analysis`
- Aktualisiertes Register der analysierten Dateien

### 5. Generierung von Metadaten für den Upload in SharePoint

**Modul:** `metadata_generator.py`

**Prozess:**
1. Das System findet Fotografien, die analysiert wurden, aber noch nicht hochgeladen sind
2. Lädt das Metadatenschema aus der Datei `sharepoint_choices.json`
3. Für jede Fotografie:
   - Generiert einen neuen Dateinamen nach dem Muster `Erni_Referenzfoto_{number}`
   - Lädt die Analyseergebnisse von OpenAI und die EXIF-Metadaten hoch
   - Verknüpft die Daten aus beiden Quellen unter Berücksichtigung der Prioritäten intelligent
   - Versucht, GPS-Koordinaten zu geokodieren, um den Standort zu bestimmen
   - Validiert die Werte der Felder gemäß dem SharePoint-Schema
   - Wandelt Felder mit Mehrfachauswahl in ein für SharePoint verständliches Format um
   - Speichert die Metadaten in einer JSON-Datei im Verzeichnis `/app/data/upload/metadata`
   - Kopiert die YAML-Datei mit den EXIF-Metadaten in dasselbe Verzeichnis
   - Kopiert das Foto in das Verzeichnis `/app/data/upload` mit neuem Namen

**Besonderheiten:**
- Intelligente Verknüpfung von Daten aus verschiedenen Quellen
- Prioritäten der Quellen für verschiedene Felder (z. B. Datum aus EXIF, Beschreibung aus OpenAI)
- Geokodierung von GPS-Koordinaten mit der Nominatim API
- Validierung der Metadaten gemäß dem SharePoint-Schema

**Ergebnis:**
- Fotografien mit neuen Namen im Verzeichnis `/app/data/upload`
- JSON-Dateien mit Metadaten im Verzeichnis `/app/data/upload/metadata`
- YAML-Dateien mit EXIF-Metadaten im Verzeichnis `/app/data/upload/metadata`

### 6. Hochladen von Fotografien in SharePoint

**Modul:** `sharepoint_uploader.py`

**Prozess:**
1. Das System findet Fotografien im Verzeichnis `/app/data/upload`
2. Verbindet sich mit SharePoint
3. Für jede Fotografie:
   - Lädt die Datei in die Bibliothek "Referenzfotos" hoch
   - Lädt die entsprechende JSON-Datei mit Metadaten hoch
   - Aktualisiert die Metadaten der Datei in SharePoint
   - Lädt die YAML-Datei mit EXIF-Metadaten hoch
   - Fügt einen Eintrag in das Register der hochgeladenen Dateien hinzu
   - Verschiebt die Dateien aus dem Verzeichnis `/app/data/upload` in `/app/data/uploaded`

**Besonderheiten:**
- Batch-Hochladen von Dateien (in Gruppen von 10)
- Mechanismus für Wiederholungsversuche bei Fehlern
- Aktualisierung des Registers der hochgeladenen Dateien
- Überprüfung auf bereits hochgeladene Dateien, um Duplikate zu vermeiden

**Ergebnis:**
- Fotografien, die mit angereicherten Metadaten in SharePoint hochgeladen wurden
- Dateien, die in das Verzeichnis `/app/data/uploaded` verschoben wurden
- Aktualisiertes Register der hochgeladenen Dateien

### 7. Automatisierter Prozess

**Modul:** `auto_process.py`

**Prozess:**
1. Das System startet nacheinander alle Module:
   - `metadata_schema.py` - Hochladen des Metadatenschemas
   - `photo_metadata.py` - Hochladen von Fotografien und Extrahieren von EXIF
   - `openai_analyzer.py` - Analyse von Fotografien mit OpenAI
   - `metadata_generator.py` - Generierung von Metadaten
   - `sharepoint_uploader.py` - Hochladen von Fotografien in SharePoint

**Besonderheiten:**
- Vollständig automatisierter Prozess
- Fehlerbehandlung in jedem Schritt
- Protokollierung aller Aktionen

**Ergebnis:**
- Vollständiger Verarbeitungszyklus von Fotografien von der Hochladung bis zur Rückladung mit angereicherten Metadaten

### 8. Web-Interface

**Modul:** `web_server.py`

**Prozess:**
1. Das System startet einen Flask-Webserver
2. Stellt eine Benutzeroberfläche für die Verwaltung des Systems bereit:
   - Dashboard mit Statistiken und schnellem Zugriff auf Funktionen
   - Fotoverwaltung (Anzeige, Analyse, Upload)
   - Protokollverwaltung
   - Prozessverwaltung
   - Systemeinstellungen

**Besonderheiten:**
- Benutzerfreundliche Oberfläche mit Bootstrap 5
- CSRF-Schutz für Formulare
- Verschiedene Ansichten für verschiedene Fotostadien
- Einstellungen für OpenAI-Prompts und Modellparameter
- Möglichkeit zur Bereinigung von Datenverzeichnissen

**Ergebnis:**
- Webbasierte Benutzeroberfläche für die Verwaltung des gesamten Systems

## Schlüsseltechnische Aspekte

### 1. Verarbeitung von EXIF-Metadaten

- Extraktion von Metadaten mit Hilfe der PIL-Bibliothek
- Formatierung von GPS-Koordinaten in ein lesbares Format
- Speicherung von Metadaten im YAML-Format
- Nutzung von Metadaten zur Anreicherung des OpenAI-Prompts

### 2. Integration mit OpenAI

- Verwendung des Modells GPT-4o zur Analyse von Bildern
- Erstellung des Prompts mit Einbeziehung von EXIF-Daten
- Optimierung von Bildern vor dem Versand
- Parsing und Validierung der JSON-Antwort
- Verschiedene Prompt-Typen für unterschiedliche Analyseanforderungen

### 3. Intelligente Verknüpfung von Daten

- Bestimmung der Prioritäten der Quellen für verschiedene Felder
- Mapping von EXIF-Tags auf SharePoint-Felder
- Validierung der Werte gemäß dem Schema
- Geokodierung von GPS-Koordinaten

### 4. Integration mit SharePoint

- Authentifizierung mit Hilfe der Anmeldeinformationen
- Hochladen und Herunterladen von Dateien
- Aktualisierung der Metadaten von Dateien
- Arbeiten mit Bibliotheken und Listen

### 5. Leistungsoptimierung

- Batchverarbeitung von Dateien
- Parallelverarbeitung mit Hilfe von ThreadPoolExecutor
- Caching der Ergebnisse
- Mechanismen für Wiederholungsversuche

### 6. Fehlertoleranz

- Fehlerbehandlung in jedem Schritt
- Protokollierung aller Aktionen
- Speicherung von Zwischenergebnissen
- Register der verarbeiteten Dateien zur Vermeidung von Doppelverarbeitungen

### 7. Web-Interface

- Benutzerfreundliche Oberfläche mit Bootstrap 5
- CSRF-Schutz für Formulare
- Verschiedene Ansichten für verschiedene Fotostadien
- Einstellungen für OpenAI-Prompts und Modellparameter

## Datenflussdiagramm

```
SharePoint (Referenzfotos) --> Hochladen von Fotografien --> Extraktion von EXIF --> Analyse OpenAI --> Generierung von Metadaten --> Hochladen in SharePoint
    |                                                       |                   |                      |
    |                                                       v                   v                      |
    |                                                EXIF-Metadaten --> Intelligente Verknüpfung       |
    |                                                                           |                      |
    v                                                                           v                      v
Metadatenschema ------------------------------------------------> Validierung der Metadaten --> Aktualisierung der Metadaten
```

## Fazit

Dieses Projekt stellt eine umfassende Lösung zur Automatisierung der Verarbeitung von Fotografien von Bauprojekten dar. Das System integriert verschiedene Technologien (SharePoint, OpenAI, Geokodierung), um einen vollständigen Verarbeitungszyklus für Fotografien mit minimalem menschlichen Eingriff zu schaffen.

Zu den wichtigsten Merkmalen gehören die intelligente Verknüpfung von Daten aus verschiedenen Quellen, die Nutzung von künstlicher Intelligenz zur Analyse von Bildern und die automatische Anreicherung von Metadaten unter Berücksichtigung des Kontexts der Fotografien.

Das System wurde mit Blick auf Skalierbarkeit, Fehlertoleranz und Leistung entworfen, was eine effiziente und zuverlässige Verarbeitung großer Mengen von Fotografien ermöglicht.

Die Webschnittstelle bietet eine benutzerfreundliche Möglichkeit zur Verwaltung des gesamten Systems und ermöglicht es Benutzern, den Verarbeitungsprozess zu überwachen und zu steuern.
