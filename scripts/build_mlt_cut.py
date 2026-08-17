#!/usr/bin/env python3
"""
build_mlt_cut.py

Baut aus einer "Blanko"-Shotcut-Projektdatei (.mlt, ein einzelner Clip in voller
Laenge, so wie Shotcut sie beim ersten Speichern eines neuen Projekts erzeugt)
eine geschnittene MLT-Datei mit den angegebenen In/Out-Zeitbereichen.

WICHTIG: Jeder Clip bekommt eine eigene <chain>-Producer-ID (chain0, chain1, ...),
auch wenn alle Clips auf dieselbe Quelldatei zeigen. Das ist kein Stilfehler,
sondern ein notwendiger Bugfix. Wenn mehrere Timeline-Clips denselben Producer
referenzieren, ist das laut MLT-Spezifikation technisch gueltig, fuehrt aber in
Shotcuts Timeline-UI beim Verschieben oder Trimmen zu Spruengen (typischerweise
springt der letzte Clip an den Anfang der Timeline) und Undo (Strg+Z) stellt den
vorherigen Zustand danach nicht mehr zuverlaessig wieder her. Mit einer eigenen
Chain-ID pro Clip-Instanz tritt das Problem nicht auf. Verifiziert wurde das
empirisch mit der MLT-Referenz-Engine (melt) und in der echten Shotcut-Anwendung.

Verwendung mit einer CSV-Datei (eine Zeile "IN,OUT" pro Clip, HH:MM:SS.mmm):

    python3 build_mlt_cut.py --blank Projekt_Blanko.mlt --out Projekt_geschnitten.mlt \
        --clips clips.csv

clips.csv Beispiel:
    00:04:39.600,00:05:22.700
    00:05:27.200,00:05:57.480
    # Zeilen mit # werden ignoriert, leere Zeilen auch

Oder einzelne Clips direkt per Kommandozeile (mehrfach angebbar):

    python3 build_mlt_cut.py --blank Blanko.mlt --out geschnitten.mlt \
        --clip 00:04:39.600 00:05:22.700 --clip 00:05:27.200 00:05:57.480

Optional laesst sich zwischen allen Clips ein Leerraum einfuegen, den man in
Shotcut spaeter von Hand als Puffer fuer Blenden/Nachjustieren nutzen kann:

    ... --gap 2.0     (fuegt 2 Sekunden <blank> zwischen je zwei Clips ein)

Nach dem Schreiben validiert das Skript die erzeugte Datei automatisch: es prueft,
dass jeder Clip einen eigenen Producer hat und dass die Summe aller Clip- und
Gap-Laengen zur Gesamtlaenge des Tractors passt.
"""

import argparse
import copy
import sys
import xml.etree.ElementTree as ET


def to_seconds(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def to_timecode(seconds):
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def load_clips(args):
    clips = []
    if args.clips:
        with open(args.clips, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != 2:
                    sys.exit(f"Ungueltige Zeile in {args.clips}: {line!r} (erwarte 'IN,OUT')")
                clips.append((parts[0], parts[1]))
    if args.clip:
        for pair in args.clip:
            clips.append((pair[0], pair[1]))
    if not clips:
        sys.exit("Keine Clips angegeben (weder --clips noch --clip).")
    return clips


def main():
    parser = argparse.ArgumentParser(description="Baut eine geschnittene MLT-Datei aus einer Blanko-Vorlage.")
    parser.add_argument("--blank", required=True, help="Pfad zur Blanko-MLT-Datei (ein Clip in voller Laenge)")
    parser.add_argument("--out", required=True, help="Pfad fuer die neue, geschnittene MLT-Datei")
    parser.add_argument("--clips", help="CSV-Datei mit einer Zeile 'IN,OUT' pro Clip")
    parser.add_argument("--clip", nargs=2, action="append", metavar=("IN", "OUT"),
                         help="Einzelner Clip als IN OUT (kann mehrfach angegeben werden)")
    parser.add_argument("--gap", type=float, default=0.0,
                         help="Sekunden Leerraum (<blank>) zwischen den Clips, z.B. 2.0 fuer 2 Sekunden Puffer")
    args = parser.parse_args()

    clips = load_clips(args)

    tree = ET.parse(args.blank)
    root = tree.getroot()

    profile = root.find("profile")
    fr_num = int(profile.get("frame_rate_num"))
    fr_den = int(profile.get("frame_rate_den"))
    frame_duration = fr_den / fr_num

    chains = root.findall("chain")
    if len(chains) != 1:
        sys.exit(f"Erwarte genau eine <chain> in der Blanko-Datei, gefunden: {len(chains)}. "
                  f"Bitte eine echte Blanko-Datei mit nur einem Clip in voller Laenge verwenden.")
    template_chain = chains[0]
    chain_out_attr = template_chain.get("out")  # volle Quelllaenge, bleibt fuer jede Kopie identisch

    playlist0 = None
    for pl in root.findall("playlist"):
        if pl.get("id") == "playlist0":
            playlist0 = pl
    if playlist0 is None:
        sys.exit('Kein <playlist id="playlist0"> in der Blanko-Datei gefunden.')

    # Alte Chain und alte Entries entfernen, playlist0 wird komplett neu aufgebaut
    root.remove(template_chain)
    for child in list(playlist0):
        playlist0.remove(child)

    total_seconds = 0.0
    new_chains = []
    for i, (in_t, out_t) in enumerate(clips):
        chain_id = f"chain{i}"
        new_chain = copy.deepcopy(template_chain)
        new_chain.set("id", chain_id)
        new_chain.set("out", chain_out_attr)
        new_chains.append(new_chain)

        entry = ET.SubElement(playlist0, "entry")
        entry.set("producer", chain_id)
        entry.set("in", in_t)
        entry.set("out", out_t)

        clip_len = to_seconds(out_t) - to_seconds(in_t)
        if clip_len <= 0:
            sys.exit(f"Clip {i} hat out <= in ({in_t} -> {out_t}), das kann nicht stimmen.")
        total_seconds += clip_len

        if args.gap > 0 and i < len(clips) - 1:
            blank = ET.SubElement(playlist0, "blank")
            blank.set("length", to_timecode(args.gap))
            total_seconds += args.gap

    # Neue Chains an der Stelle einfuegen, an der vorher die Vorlagen-Chain stand
    insert_index = list(root).index(playlist0)
    for offset, ch in enumerate(new_chains):
        root.insert(insert_index + offset, ch)

    out_timecode = to_timecode(total_seconds - frame_duration)
    length_timecode = to_timecode(total_seconds)

    for producer in root.findall("producer"):
        if producer.get("id") == "black":
            producer.set("out", out_timecode)
            length_prop = producer.find("./property[@name='length']")
            if length_prop is not None:
                length_prop.text = length_timecode

    for pl in root.findall("playlist"):
        if pl.get("id") == "background":
            bg_entry = pl.find("entry")
            if bg_entry is not None:
                bg_entry.set("out", out_timecode)

    tractor = root.find("tractor")
    tractor.set("out", out_timecode)

    tree.write(args.out, xml_declaration=True, encoding="UTF-8")

    print(f"Geschrieben: {args.out}")
    print(f"Clips: {len(clips)}, Gesamtdauer: {total_seconds:.3f}s ({total_seconds/60:.2f} min)")

    # Sofort-Validierung: Datei erneut einlesen und Summen gegenchecken
    check_root = ET.parse(args.out).getroot()
    check_playlist0 = next(pl for pl in check_root.findall("playlist") if pl.get("id") == "playlist0")
    entries = check_playlist0.findall("entry")
    blanks = check_playlist0.findall("blank")

    producers_used = [e.get("producer") for e in entries]
    if len(producers_used) != len(set(producers_used)):
        print("WARNUNG: Mehrere Entries teilen sich denselben Producer - das reproduziert den bekannten Shotcut-Bug!")
    else:
        print(f"OK: alle {len(entries)} Clips haben eine eigene Chain-ID.")

    check_total = sum(to_seconds(e.get("out")) - to_seconds(e.get("in")) for e in entries)
    check_total += sum(to_seconds(b.get("length")) for b in blanks)
    check_tractor_out = to_seconds(check_root.find("tractor").get("out"))
    diff = abs(check_total - check_tractor_out - frame_duration)
    if diff > 0.001:
        print(f"WARNUNG: Summe der Clips/Gaps ({check_total:.3f}s) passt nicht zum Tractor-Out ({check_tractor_out:.3f}s)!")
    else:
        print("OK: Summe der Clips/Gaps stimmt mit der Tractor-Laenge ueberein.")


if __name__ == "__main__":
    main()
