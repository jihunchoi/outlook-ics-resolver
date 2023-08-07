import json

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI()
app.vtimezone_mapping = None
app.delimiter = "BEGIN:VTIMEZONE"


def _load_vtimezone_mapping():
    if app.vtimezone_mapping is None:
        app.vtimezone_mapping = {}
        with open("vtimezones.ndjson", "r") as f:
            for line in f:
                print(line)
                entry = json.loads(line)
                app.vtimezone_mapping[entry["name"]] = entry["content"]
    return app.vtimezone_mapping


@app.get("/q/{ics_url:path}")
async def page(ics_url: str, timezones: str = ""):
    if not ics_url.startswith("https://outlook.office365.com"):
        raise HTTPException(status_code=500, detail=f"Unsupported URL: {ics_url}")

    timezones = [tz.strip() for tz in timezones.split(",")]
    timezones = list(filter(None, timezones))

    r = requests.get(ics_url)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.content)

    ics_content = r.content.decode(r.encoding)
    header, rest = ics_content.split(app.delimiter, maxsplit=1)
    rest = app.delimiter + rest

    vtimezone_entries = []
    vtimezone_mapping = _load_vtimezone_mapping()
    for tz in timezones:
        if tz not in vtimezone_mapping:
            raise HTTPException(status_code=500, detail=f"Unknown timezone: {tz}")
        vtimezone_entries.append(vtimezone_mapping[tz])

    new_ics_content = header + "\n".join(vtimezone_entries) + "\n" + rest
    new_ics_content = new_ics_content.encode(r.encoding)

    return PlainTextResponse(content=new_ics_content, media_type="text/calendar")
