#!/usr/bin/env python3
import json, os, shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
QUEUE=ROOT/"today-history-queue"
MANIFEST=QUEUE/"manifest.json"
ARCHIVE=ROOT/"today-in-florida-history.html"
HOME=ROOT/"index.html"

def main():
    today=os.getenv("FLH_TODAY") or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    data=json.loads(MANIFEST.read_text())
    item=next((x for x in data["entries"] if x["publish_date"]==today and x.get("status")=="Approved for Publication"),None)
    if not item:
        print(f"No approved Today in Florida History entry for {today}.")
        return
    staged=QUEUE/item["staged_file"]
    live=ROOT/item["live_file"]
    if not staged.exists():
        raise SystemExit(f"Approved queue item is missing staged file: {staged}")
    if not live.exists():
        shutil.copyfile(staged,live)
    archive=ARCHIVE.read_text()
    marker='<section class="article">'
    entry=f'''<h2>Featured Entry — {item["display_date"]}</h2><h2>{item["display_date"]} — {item["title"]}</h2><p>{item["summary"]}</p><p><a class="btn" href="{item["live_file"]}">Read {item["display_date"]}: {item["link_title"]}</a></p><hr>'''
    if f'href="{item["live_file"]}"' not in archive:
        pos=archive.find(marker)
        if pos == -1:
            raise SystemExit("Today archive section marker not found")
        insert_at=pos+len(marker)
        old_start=archive.find("<h2>Featured Entry — ",insert_at)
        if old_start != -1:
            old_end=archive.find("<hr>",old_start)
            if old_end != -1:
                old_feature=archive[old_start:old_end+4]
                archive=archive[:old_start]+archive[old_end+4:]
                insert_at=archive.find(marker)+len(marker)
                archive=archive[:insert_at]+entry+old_feature+archive[insert_at:]
            else:
                archive=archive[:insert_at]+entry+archive[insert_at:]
        else:
            archive=archive[:insert_at]+entry+archive[insert_at:]
    ARCHIVE.write_text(archive)
    home=HOME.read_text()
    start=home.find('<div class="panel"><div class="kicker">Today in Florida History')
    if start!=-1:
        end=home.find('</div>',start)+6
        panel=f'''<div class="panel"><div class="kicker">Today in Florida History · {item["display_date"]}</div><h2>{item["title"]}</h2><p>{item["summary"]}</p><p><a class="btn" href="{item["live_file"]}">Read: {item["link_title"]}</a></p></div>'''
        home=home[:start]+panel+home[end:]
        HOME.write_text(home)
    data["last_featured"]=item["display_date"]
    MANIFEST.write_text(json.dumps(data,indent=2)+"\n")
    print(f"Published {item['live_file']} for {today}")

if __name__=="__main__": main()
