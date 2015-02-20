CALMA data wrangling

CALMA project:
* [http://calma.linkedmusic.org]()
* [http://etree.linkedmusic.org/about/]()

Data sources used
* [http://calma.linkedmusic.org/data/]()
* [http://calma.linkedmusic.org/data/track_00001237-2bbe-402f-8586-f5ddd3f22800/]()
* [http://calma.linkedmusic.org/data/track_00001237-2bbe-402f-8586-f5ddd3f22800/analyses.ttl]()
* [http://calma.linkedmusic.org/data/track_00001237-2bbe-402f-8586-f5ddd3f22800/analysis_019e4657-7d15-42e7-b4c9-3af1a1bb585d.ttl]()
* _etc._


## TODO

- [x] Read analyses.ttl and load multiple analyses for track
- [ ] Decode rdf:Seq and expand to JSON list
- [ ] Handle bNodes to propviode more useful rendering
- [ ] Import linked FLAC files and provide Annalist render for player controls (8 mins, 47Mb)
- [ ] Locate and import MusicBrainz description
- [ ] Annalist support listing with linked label instead of linked id
- [ ] Annalist support enumeration with label instead of id
- [x] Add link, label, description for plugin
- [x] Add label and comment to all views
- [ ] Generalize identifier extraction logic to use per-type rules
- [ ] Generalize field generation logioc with per-property rules

