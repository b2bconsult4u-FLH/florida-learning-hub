# Today in Florida History: October 20–31 production batch

Prepared October 20, 2026 at the user’s instruction to complete and upload the articles for automatic publication. October 19 was already published and is preserved.

## Queue coverage

| Publication date (Eastern) | Article | Embedded image |
|---|---|---|
| 2026-10-20 | The Plane Crash That Shook Jacksonville’s Southern Rock Legacy | No |
| 2026-10-21 | Osceola Is Captured Under a Flag of Truce | Yes |
| 2026-10-22 | Florida Faces the Cuban Missile Crisis | Yes |
| 2026-10-23 | Olustee Becomes Florida’s First State Historic Site | No |
| 2026-10-24 | Deep Space 1 Leaves Cape Canaveral | Yes |
| 2026-10-25 | A Hurricane Floods Tampa Bay Communities | Yes |
| 2026-10-26 | A National Park Protects the Dry Tortugas | Yes |
| 2026-10-27 | A Treaty Defines Spanish Florida’s Northern Boundary | No |
| 2026-10-28 | Air Mail Launches Pan Am’s Scheduled Service from Key West | No |
| 2026-10-29 | John Glenn Returns to Orbit from Florida at 77 | Yes |
| 2026-10-30 | A New Shands Bridge Spans the St. Johns | No |
| 2026-10-31 | A Tractor Parade Puts Rural Florida on Display | No |

## Validation before upload

- Existing `python scripts/test_today_history.py`: seven tests pass.
- All twelve dates exercised sequentially in an isolated repository copy; article, homepage, archive and generated sitemap verified for each date.
- Every date repeated with byte-for-byte unchanged output on retry.
- Every previously published daily article preserved byte-for-byte.
- Future root article files absent until their matching date is exercised.
- Exactly one queue entry per date; all citation anchors, canonical/date metadata, local image files, image credits and source links checked.
- No publisher, trigger, credential, or Cloudflare configuration changes.
- Browser layout screenshots could not be run: Chromium was absent and its download returned an invalid archive. Image files were decoded and visually inspected as a contact sheet; mobile/desktop rendering is not claimed.

## Source and image notes

Articles follow the existing October 19–31 editorial plan. They distinguish signature from ratification, dedication from battle or construction, photographed event from founding, and Florida connections from events occurring outside the state. Each article includes institutional references and discussion questions.

Six verified images are embedded and stored under `assets/history/`. No hotlinked images or image placeholders are included. Copyrighted band publicity and album artwork were not reused. Florida Memory image retrieval returned HTTP 403 for the planned Olustee, Shands and tractor images; these three articles contain textual source references without claiming visual inspection of those photographs. The tractor article does not assert identities, brands, or visible details beyond the catalog description. The band, treaty and Pan Am articles also use text-only layouts.

| Asset | Credit | Source / reuse basis |
|---|---|---|
| `osceola-george-catlin-1838.jpg` | George Catlin; Smithsonian American Art Museum, via National Park Service | [https://www.nps.gov/people/osceola.htm](https://www.nps.gov/people/osceola.htm); Public-domain nineteenth-century artwork; reproduced from the NPS biography, which credits the Smithsonian American Art Museum. |
| `everglades-hm69-launch-area.jpg` | National Park Service | [https://www.nps.gov/ever/learn/historyculture/hm69.htm](https://www.nps.gov/ever/learn/historyculture/hm69.htm); NPS-credited federal agency photograph; educational editorial reuse with credit. |
| `nasa-xenon-ion-engine-prototype.jpg` | NASA | [https://www.nasa.gov/history/nasa-history-deep-space-1-validated-the-promise-of-ion-thrusters/](https://www.nasa.gov/history/nasa-history-deep-space-1-validated-the-promise-of-ion-thrusters/); NASA-credited image published for public informational use; credit retained. |
| `tampa-terminals-1921-hurricane.jpg` | Tampa-Hillsborough County Public Library System, via NOAA / National Weather Service | [https://www.weather.gov/media/tbw/1921/1921_Hurr_99th_Anniversary.pdf](https://www.weather.gov/media/tbw/1921/1921_Hurr_99th_Anniversary.pdf); Historical 1921 photograph reproduced in the NWS educational publication; library credit retained. Published U.S. work from before 1931. |
| `fort-jefferson-sallyport-nps.jpg` | National Park Service / Denise Diaz | [https://www.nps.gov/drto/learn/historyculture/index.htm](https://www.nps.gov/drto/learn/historyculture/index.htm); NPS staff photograph credited to Denise Diaz on the source page; educational editorial use with credit. |
| `discovery-sts95-launch-1998.jpg` | NASA | [https://www.nasa.gov/history/25-years-ago-sts-95-john-glenn-returns-to-space/](https://www.nasa.gov/history/25-years-ago-sts-95-john-glenn-returns-to-space/); NASA mission photography; public informational/editorial use with credit retained. |

## Publication behavior

The unchanged workflow publishes only the approved item whose date matches the current America/New_York date (or an explicit controlled recovery date). The queue upload triggers the existing workflow on main, so the overdue October 20 item can publish immediately. October 21–31 remain assigned to their respective dates. Staged files reside in the repository’s existing queue directory; no future root articles or future archive/sitemap entries are added by this upload.

The existing live verifier remains responsible for checking each publication after deployment. Successful local verification is not a promise of future trigger execution or deployment availability.
