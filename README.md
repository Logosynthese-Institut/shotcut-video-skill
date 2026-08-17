# shotcut-video

Ein Claude-Skill, der aus einem Video-Transkript und einer leeren Shotcut-Projektdatei automatisch einen begründeten Schnittvorschlag sowie die fertige, geschnittene Shotcut-Projektdatei (`.mlt`) erstellt.

**Autor:** Karsten Blauel

## Was der Skill macht

1. Du gibst Claude ein Transkript mit Zeitstempeln (z. B. eine `.srt`-Datei) und eine leere Shotcut-Projektdatei (dein Rohvideo, einmal importiert und gespeichert).
2. Claude liest das Transkript, schlägt Schnittpunkte mit Begründung vor (Langversion, Kurzversion oder Trailer) und wartet auf deine Bestätigung.
3. Nach Bestätigung baut Claude automatisch die fertige `.mlt`-Datei, die du in Shotcut öffnest, kontrollierst und final nachjustierst.

Der Skill liefert immer die editierbare Projektdatei, nie ein fertig gerendertes Video.

## Voraussetzungen

- [Shotcut](https://shotcut.org/) (kostenlose Version reicht)
- Ein Transkript mit Zeitstempeln im Format `HH:MM:SS`
- Eine leere Shotcut-Projektdatei mit dem vollständigen Rohvideo auf der Zeitleiste

Eine ausführliche Schritt-für-Schritt-Anleitung liegt diesem Repository bei (`Anleitung_Videoschnitt-Skill.docx`).

## Installation

1. Diese Repository herunterladen oder die Datei `shotcut-video.skill` aus den [Releases](../../releases) laden.
2. In einem Claude-Chat (claude.ai oder Claude-Desktop mit Cowork-Modus) die `.skill`-Datei per Drag & Drop in den Chat ziehen.
3. Auf den Button **„Save skill“** klicken – der Skill ist danach in diesem Claude-Account automatisch verfügbar, sobald du über Videoschnitt, Shotcut, Trailer, Lang-/Kurzversion sprichst.

Alternativ lassen sich die drei enthaltenen Dateien (`SKILL.md`, `scripts/build_mlt_cut.py`, `references/mlt-format.md`) auch manuell in ein lokales Skills-Verzeichnis kopieren, falls du Claude Code oder das Claude Agent SDK direkt nutzt.

## Technischer Hintergrund

Der Skill enthält einen Fix für ein reales Shotcut/MLT-Kompatibilitätsproblem: Teilen sich mehrere Timeline-Clips einen einzelnen Producer, springen beim Verschieben in Shotcuts Timeline-UI teilweise andere Clips mit. `build_mlt_cut.py` vergibt automatisch pro Clip eine eigene Chain-ID und umgeht das Problem. Details dazu stehen in `references/mlt-format.md`.

## Haftungsausschluss

Dieser Skill und die zugehörige Anleitung wurden nach bestem Wissen erstellt, es wird jedoch keine Gewähr für Vollständigkeit, Aktualität oder Fehlerfreiheit übernommen. Die Nutzung erfolgt eigenverantwortlich und auf eigenes Risiko. Für Datenverlust, fehlerhafte Schnitte oder sonstige Schäden, die durch die Anwendung dieses Skills entstehen, wird keine Haftung übernommen. Siehe auch die Gewährleistungsausschluss-Klausel in [LICENSE](LICENSE).

## Lizenz

Veröffentlicht unter der [MIT-Lizenz](LICENSE) © Karsten Blauel.
