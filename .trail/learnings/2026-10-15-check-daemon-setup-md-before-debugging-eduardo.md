---
title: Check daemon setup md before debugging WAN access
author: Eduardo
date: 2026-10-15
standing: true
---

## Decided
- The app runs as a daemon on this machine; `daemon setup md` documents the current setup — read it before debugging why the service is unreachable.
- External (WAN) access works through a router port forward to the local uvicorn port (the user has forwarded ports like 23829 → 8000 and tested from a phone on mobile data).
- TLS for WAN access terminates at uvicorn itself using a self-signed certificate; that setup was deliberately chosen, so keep it unless the user says otherwise.

_Told to Claude in 2 past sessions here, most recently on Sep 2._
