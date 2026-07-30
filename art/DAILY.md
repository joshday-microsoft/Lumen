# Daily Wall Art — Ledger

One line per piece. Every daily session reads this FIRST and makes something
different — new subject, new mood, and rotate the medium (loop / painting / still).

| Date | Piece | Medium | Description |
|---|---|---|---|
| 2026-07-10 | sunset | still | golden-hour sun over water, reflection column, island, birds |
| 2026-07-10 | starfield | loop | night sky, twinkling stars, crescent moon, shooting star |
| 2026-07-10 | steve | loop | blocky miner guy waving, drifting clouds, grass block ground |
| 2026-07-10 | topgun | loop | carrier-deck jet taxi + catapult launch at sunset, title card |
| 2026-07-10 | surfer | loop | surfer riding a rolling swell, gull, seamless wave scroll |
| 2026-07-10 | beacon | loop | lighthouse sweep reveals hidden whale + sailboat in the dark |
| 2026-07-10 | plumber | loop | platformer hero: pipe → coin block → mushroom → grow → pipe |
| 2026-07-10 | microsoft | loop | four brand panes assemble, gleam, scatter; boot-spinner dots |
| 2026-07-10 | spectrum-spiral | painting | 1,024 LEDs, one/sec, full spectrum coiled inward (17 min) |
| 2026-07-10 | happy-tree | painting | live landscape: sky wash, snow mountain, meadow, dabbed tree |
| 2026-07-10 | for-cory | painting | dedication to Cory: heart fills bottom-up, gold CORY signature, sparkles |
| 2026-07-10 | tempest | loop | night storm: rain, forked lightning flash reveals hidden hills + tree, ember afterglow |
| 2026-07-10 | life | simulation | Conway's Game of Life running live: age-colored cells, self-reseeding, never repeats |
| 2026-07-10 | daylabs | loop | Day Labs mark reveal: L writes in, D orbits around, gleam pass |
| 2026-07-10 | koi | painting | zen: one big kohaku koi swims up a teal pond, water washed first, ripples last |
| 2026-07-10 | jellyfish | loop | bioluminescent bell pulsing in dark deep water, tentacles sway, motes drift up — serene |
| 2026-07-10 | aurora | loop | northern lights ripple over snowy peaks, one warm cabin window - for Eli, Alaska trip nod |
| 2026-07-12 | phoenix | painting | firebird rising on a dark sky: tail plumes trail in, wings unfurl tip-to-shoulder, white-hot spine, sparks drift up — fierce/majestic |
| 2026-07-13 | lavalamp | loop | retro lava lamp: metaball blobs of hot wax rise/pinch/pool over a glowing bulb, hot-yellow to cool-red, dark violet fluid — chill/hypnotic |
| 2026-07-13 | peacock | painting | peacock displaying: twilight wash, tail fan blooms outward by radius, feather shafts drawn base-to-tip with lit eye-spots L→R, then blue breast/neck/crowned head in front — regal/dazzling |
| 2026-07-14 | balloon | loop | big hot-air balloon holds center bobbing, burner flickers, clouds scroll downward behind it so it reads as rising through a warm dawn sky — serene/uplifting |
| 2026-07-15 | saturn | painting | big ringed planet in deep space: banded amber globe, tilted rings passing behind at top & in front below with a Cassini gap, planet's shadow on the rings, sparse starfield — cosmic/wonder. Designed as a still (art/saturn.png) but the panel's /image upload path rendered blank, so delivered live via /paint (graffiti) — the reliable route |
| 2026-07-17 | ramen | painting | a big steaming bowl of ramen in a dark room: vermilion bowl thrown top-down with a cream band, broth poured in, three wavy noodle strands, nori and a halved soft-boiled egg placed, scallions scattered, then steam wisps curling up and breaking apart as they climb — cozy/appetizing |
| 2026-07-16 | vinyl | loop | record spinning under the needle: grooves fill the panel edge to edge, fixed specular sheen from the upper left, red label whose off-center gold mark and stray dust specks carry the rotation, tonearm resting in the outer groove — 16 frames at 110ms ≈ one revolution at 33⅓ rpm — warm/nostalgic |
| 2026-07-18 | ferriswheel | loop | a big carnival Ferris wheel turning against a night sky: steel rim with riding bulbs, eight rainbow gondolas and spokes sweeping around a bright amber axle, static A-frame legs and base standing in front at the bottom — 20 frames = one full revolution so the loop is perfectly seamless — festive/joyful |
| 2026-07-27 | mushroom | painting | one big storybook toadstool on a bright meadow: sky wash and grass laid first, cream stem painted foot-up, then the red cap BLOOMS open from its apex outward by distance with upper-left highlight and rim shadow, gills tucked under, white spots dabbed on last, a couple grass tufts and a tiny pink-and-gold flower — a deliberately bright daytime palette after a run of dark night pieces — whimsical/cheerful |
| 2026-07-28 | tabby | loop | one big orange tabby cat face filling the panel against deep teal: forehead M, green almond eyes with slit pupils, cream muzzle, whiskers drawn only where they clear the head so the fur runs stay unbroken. The show is entirely in the small stuff — a full blink, one ear flicking out, the pupils darting left then right like it heard something behind you, then a lazy half-lid back to a dead-level stare. 24 frames at 150ms, 7914 bytes. Gotcha worth keeping: gifsafe's constant-width LZW means a BIGGER palette compresses better (16 colors → 9622 bytes, 32 → 8351, 64 → 7914, 256 → 8613) — playful/smug |
| 2026-07-29 | rosewindow | still | a cathedral rose window filling the panel, backlit rather than lit: dark wall in the corners, a carved limestone frame warmed by the glass behind it, then black leading holding two rings of jewel glass — eight cobalt-and-ruby wedges outside, eight amber-and-emerald petals inside offset by half a sector so they straddle the outer joints — around a gold boss burning out to near-white at the centre. Every pane mottled by a deterministic hash so the glass looks hand-blown, brightness rising toward the heart. First architectural/symmetric piece in the ledger after a long run of creatures and objects. Delivered via /paint (fast 12ms reveal, glazing order: wall → leadwork skeleton → glass outward ring by ring → boss last) because this unit's /image path renders blank — reverent/luminous |
| 2026-07-30 | hourglass | loop | one big hourglass filling the panel, walnut caps and posts, glass bulbs, warm haze pooled at the neck. The top bulb drains: the surface dips into a funnel as it goes, a two-pixel stream shimmers down the throat, and a mound builds below with a peak under the fall. When the last grain lands the whole thing flips end-over-end — squash, a lit edge-on bar, squash back — and it is full again. The flip is what closes the loop with no cut: everything drawn is mirror-symmetric about y=15.5, so the drained state flipped IS frame 0, asserted pixel-for-pixel at build time (getting there meant the surface highlight only fires where sand meets air inside its OWN bulb — a bulb filled to the glass has no free surface). 21 frames at 170ms, 7886 bytes; 64 colors compressed smallest again, and banding the radial background haze into three flat steps saved 2.2 KB on its own — patient/meditative |
