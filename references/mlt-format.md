[MLT-FO~1.MD](https://github.com/user-attachments/files/31138061/MLT-FO.1.MD)
# MLT / Shotcut: technische Referenz

Diese Datei ist die vertiefte Referenz zum `shotcut-video`-Skill. Lies sie, wenn du im Detail verstehen musst, wie eine MLT-Datei aufgebaut ist, warum der Chain-ID-Bugfix nötig ist, oder wenn dir ein Nutzer ein konkretes Shotcut-UI-Problem beschreibt.

## 1. Grundstruktur einer Shotcut-Projektdatei (.mlt)

Eine .mlt-Datei ist XML mit diesem Grundgerüst:

```xml
<mlt ...>
  <profile .../>                      <!-- Auflösung, Framerate, Seitenverhältnis -->
  <playlist id="main_bin">...</playlist>   <!-- Shotcuts Projekt-Bin, für den Schnitt irrelevant -->
  <producer id="black" .../>          <!-- schwarzer Hintergrund, so lang wie das ganze Projekt -->
  <playlist id="background">...</playlist> <!-- Track A0, enthält nur "black" -->
  <chain id="chain0" .../>            <!-- der eigentliche Quellclip mit Codec-Metadaten -->
  <playlist id="playlist0">...</playlist>  <!-- Track V1, die eigentliche Schnittfolge -->
  <tractor id="tractor0" ...>          <!-- die Gesamtkomposition -->
    <track producer="background"/>
    <track producer="playlist0"/>
    <transition .../>                 <!-- Audio-Mix -->
    <transition .../>                 <!-- Video-Compositing (deaktiviert, disable=1) -->
  </tractor>
</mlt>
```

Für einen einfachen Schnitt (ein Video-Track, keine Übergänge zwischen Clips) sind nur `producer id="black"`, `playlist id="background"`, die `chain`-Elemente, `playlist id="playlist0"` und der `tractor` relevant. Die restliche Struktur bleibt beim Schneiden unverändert.

## 2. Zeitcode-Format

`in`/`out`-Attribute und `<blank length="...">` akzeptieren zwei Formate: reine Framezahlen (Ganzzahl) oder Uhrzeit-Werte im Format `HH:MM:SS.mmm`. Ein Wert mit Dezimalpunkt wird als Uhrzeit interpretiert. In diesem Skill wird ausschließlich das Uhrzeit-Format verwendet, weil sich Zeitstempel direkt aus SRT-Transkripten übernehmen lassen (dort im Format `HH:MM:SS,mmm` mit Komma statt Punkt).

Wichtig für Gesamtlängen-Berechnungen: `out` ist der **letzte eingeschlossene Frame**, nicht das Ende. Bei einer Framerate von 25 fps und einer Gesamtlänge von z. B. 73.144 Sekunden ist `out = 73.144 - (1/25) = 73.104` Sekunden, während die `length`-Property weiterhin die volle Dauer `73.144` trägt. Das Build-Skript (`scripts/build_mlt_cut.py`) rechnet das automatisch.

## 3. Nicht-destruktives Schneiden

Ein `<chain>` referenziert eine Quelldatei per Pfad und hat selbst ein `out`, das die volle Länge der Quelle beschreibt. Jeder `<entry producer="..." in="..." out="...">` in `playlist0` greift nur einen Zeitbereich aus dieser Quelle heraus. Das bedeutet: Man kann Schnittlisten bauen, ohne die eigentliche Videodatei zu besitzen oder zu öffnen — nur die Zeitstempel aus dem Transkript werden gebraucht. Das ist die Grundlage für den ganzen Workflow dieses Skills.

## 4. Der Chain-ID-Bug (wichtig, unbedingt lesen)

**Symptom, wie es sich beim Nutzer zeigt:** Beim Ziehen oder Trimmen eines Clips in der Shotcut-Timeline springt ein anderer Clip (typischerweise der letzte) unerwartet an eine andere Position, oft ganz nach vorn. Strg+Z (Undo) stellt danach den vorherigen Zustand nicht zuverlässig wieder her. Der Nutzer berichtet, dass ihm das bei seinen eigenen, in Shotcut selbst erstellten Projekten nie passiert, nur bei generierten Dateien.

**Ursache:** Wenn mehrere `<entry>`-Elemente in `playlist0` auf denselben `<chain id="chain0">` verweisen (weil sie ja alle aus derselben Quelldatei stammen), ist das laut MLT-Spezifikation technisch zulässig. Shotcuts Qt-basierte Timeline-UI verwendet die Producer-Identität aber offenbar auch zur internen Nachverfolgung von Clip-Instanzen beim Drag & Drop und beim Undo-Stack. Teilen sich mehrere Timeline-Clips einen Producer, kollidiert das mit dieser internen Logik.

**Fix:** Jede Clip-Instanz bekommt ihre eigene `<chain id="chainN">` mit identisch dupliziertem Codec-/Metadaten-Block, auch wenn alle auf dieselbe Quelldatei zeigen. `scripts/build_mlt_cut.py` macht das automatisch für jeden übergebenen Clip.

**Wie das verifiziert wurde:** Mit der MLT-Referenz-Engine `melt` (demselben Rendering-Backend, das auch Shotcut nutzt) wurden beide Varianten geparst und gerendert — beide sind strukturell gültig und ergeben dieselbe Gesamtlänge, der Unterschied liegt ausschließlich im UI-Verhalten von Shotcut selbst. Der Fix wurde vom Nutzer in der echten Anwendung bestätigt ("Jetzt funktioniert es sehr gut").

**melt lokal ohne Root-Rechte installieren** (falls eine tiefere Validierung als reines XML-Parsing nötig ist):

```bash
cd /tmp && mkdir -p mltroot && cd mltroot
for pkg in melt libmlt7 libmlt-data libsdl2-2.0-0 frei0r-plugins \
           libavformat58 libavcodec58 libavutil56 libswscale5 \
           libswresample3 libavfilter7 libavdevice58; do
  apt-get download "$pkg"
done
for deb in *.deb; do dpkg-deb -x "$deb" .; done
export LD_LIBRARY_PATH=/tmp/mltroot/usr/lib/x86_64-linux-gnu
export MLT_REPOSITORY=/tmp/mltroot/usr/lib/x86_64-linux-gnu/mlt-7
export MLT_DATA=/tmp/mltroot/usr/share/mlt-7
export FREI0R_PATH=/tmp/mltroot/usr/lib/frei0r-1
./usr/bin/melt-7 -consumer null projekt.mlt out=5
```

Das reicht, um eine Datei strukturell durchrechnen zu lassen, ohne dass die referenzierten Videodateien tatsächlich vorhanden sein müssen (bei fehlenden Quelldateien meldet melt das, bricht aber nicht bei reinen XML-Strukturfehlern anders ab als bei fehlenden Medien — im Zweifel zusätzlich mit `python3 -c "import xml.etree.ElementTree as ET; ET.parse('datei.mlt')"` auf Wohlgeformtheit prüfen).

## 5. Bekannte Shotcut-UI-Eigenheiten (für Gespräche mit dem Nutzer)

Diese Punkte sind keine Bugs in generierten Dateien, sondern generelle Shotcut-Verhaltensweisen, die hilfreich sind, wenn der Nutzer von Schwierigkeiten beim manuellen Nachschneiden berichtet:

- **Ripple-Trim vs. Roll-Edit:** Zieht man am Rand eines Clips, verschiebt sich (im Ripple-Modus) alles Nachfolgende automatisch mit. Um stattdessen die Grenze zwischen zwei benachbarten Clips zu verschieben (einer wird kürzer, der andere länger, Gesamtlänge bleibt gleich), braucht es Strg+Ziehen genau auf der gemeinsamen Kante (Roll Edit).
- **Mehrere Clips gleichzeitig verschieben** (markieren + ziehen) ist in Shotcut historisch unzuverlässig, gerade wenn sich beim Verschieben Überlappungen ergeben könnten. Besser: einzeln verschieben oder Werte direkt im Properties-Panel eintragen.
- **Clips, die über den sichtbaren Timeline-Bereich hinausragen:** Wird ein Clip gezogen, der teilweise außerhalb des sichtbaren Bereichs liegt, kann es zu Sprüngen kommen. Vor dem Ziehen erst komplett herauszoomen hilft.
- **Undo nach Timeline-Drag** ist in manchen Shotcut-Versionen unzuverlässig. Sicherer: Datei ungespeichert schließen und die zuletzt gespeicherte Version neu öffnen, oder von vornherein mit dem Properties-Panel statt per Drag arbeiten.

## 6. Bekannte Transkript-Eigenheit: Stundenzähler-Sprünge

Bei sehr langen Aufnahmen (über eine Stunde) kann es vorkommen, dass ein SRT-Export in einem Abschnitt die Stundenziffer fälschlich zurücksetzt (z. B. steht dort `00:14:14,075` statt korrekt `01:14:14,075`). Das fällt auf, wenn Zeitstempel im Kontext keinen Sinn ergeben — etwa wenn zwei inhaltlich unmittelbar aufeinanderfolgende Sätze im Transkript zeitlich eine Stunde auseinanderliegen würden. Im Zweifel den Kontext (vorherige/nachfolgende Zeitstempel, Gesamtlänge der Aufnahme) gegenchecken und die Stunde manuell korrigieren, bevor der Zeitstempel in eine Schnittliste übernommen wird.
