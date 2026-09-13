# Human AI — reversible port-layer experiment

Human AI is an **optional, port-only overlay** for GoldenEye Ascension. It does not replace or edit the original N64 AI interpreter, global AI lists, stage action blocks, navigation, animation or weapon code. `AI.HumanMode=0` is the default and is intended to preserve Classic GoldenEye behaviour.

The experiment asks a narrow question: **how far can GoldenEye's existing AI vocabulary be pushed toward believable human behaviour while keeping the 1997 mission scripts authoritative and making the change reversible?**

## Controls

- `F9`: toggle `CLASSIC` / `HUMAN` at runtime.
- `--human-ai`: request Human AI at startup.
- `--classic-ai`: force Classic at startup.
- `GE_HUMAN_AI=1`: environment override.
- `ge007.ini`:

```ini
[AI]
HumanMode=0
Debug=0
Intensity=1.0
MaxTactical=6
```

`HumanMode=0` is intentionally the default. `Intensity` scales sensory awareness gain, not enemy health. `MaxTactical` limits how many guards the overlay may simultaneously reposition with cover/flank/advance decisions; the original game's own active-guard/pathfinding limits remain intact.

## Why an overlay instead of rewriting `src/game`

The repository's preservation rule is that original game control flow is ground truth. Human AI therefore lives in `port/` and composes existing primitives:

- `ChrRecord` memory and ratings;
- the original AI bytecode VM (`ailist`, `aioffset`, `aireturnlist`);
- `chrCanSeeBond` and the STAN line-of-sight rules;
- `plot_course_for_actor`, `chrGoToPad`, `chrGoToBond` and waypoints;
- `check_2328_preset_set_with_method` for side/back tactical pads;
- `chrTrySurrender`, sidesteps and hops;
- the original stage action blocks for narrative/boss behaviour.

The module is chained into fast3d's existing pre-swap callback after `videoInit()`. This puts the Human AI update on the scheduler/render thread and preserves the pre-existing screenshot/frame-dump callback. No host-thread game-state mutation is required.

## Research basis

The implementation is inspired by design principles, not copied code.

### Thief: The Dark Project

Tom Leonard's postmortem describes a broader AI awareness spectrum than the common "oblivious/omniscient" split, AI communication through meaningful sounds, and a secondary room database used to propagate sound through connected spaces. His later sensory-system article describes memory as sense relationships carrying time, location and line-of-sight; visibility as a combination of lighting, movement and exposure; time-based reaction filtering; gradual awareness decay; and constrained sharing between peer AIs.

- https://www.gamedeveloper.com/design/postmortem-i-thief-the-dark-project-i-
- https://www.gamedeveloper.com/programming/building-an-ai-sensory-system-examining-the-design-of-i-thief-the-dark-project-i-

Ascension mapping: GE already has rooms/portals, STAN shade data, `lastseetarget60`, `lastheartarget60` and `lastknowntargetpos`, so Human AI extends those concepts rather than inventing a parallel navigation world.

### Splinter Cell: Blacklist

Martin Walsh's GDC 2014 talk argues that stealth perception needs more than a binary cone/radius: realistic vision/hearing plus social, environmental and contextual awareness, while also giving the player consistent feedback.

- https://gdcvault.com/play/1020195/Modeling-AI-Perception-and-Awareness

Ascension mapping: visual awareness accumulates continuously from range, central/peripheral angle, movement, approximate lighting, attention and experience. Recognition then has a human reaction delay instead of an immediate binary switch.

### F.E.A.R.

Jeff Orkin's "Three States and a Plan" describes squad behaviours such as suppression, coordinated advances, searches and grenade pressure while using planning to select actions rather than an enormous state graph.

- https://gdcvault.com/play/1013282/Three-States-and-a-Plan

Ascension mapping: the overlay keeps a small mental-state model but chooses from GoldenEye's existing physical vocabulary — `GOPOS`, side pads, run-to-Bond, sidestep/hop, grenade probabilities and surrender — instead of adding a second animation/combat engine.

### Alien: Isolation

Analyses of Creative Assembly's AI describe a macro director that knows the player's location while the individual alien receives only coarse guidance and must locate the player with its own sensors. The useful lesson is not the horror pacing system itself; it is the separation between **global pressure** and **individual knowledge**.

- https://www.gamedeveloper.com/design/revisiting-the-ai-of-alien-isolation
- https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation

Ascension mapping: local communication transfers a degraded area estimate, not exact Bond coordinates. The module deliberately keeps uncertainty and does not broadcast omniscience across the level.

### The Last of Us and Hitman: Absolution

Naughty Dog's Human Enemy AI talk explicitly covers navigation, real-time level analysis, combat, search and stealth. IO Interactive's Hitman talk describes layered NPC AI that must transition plausibly among social stealth, action stealth and tactical combat.

- https://gdcvault.com/play/1020338/The-Last-of-Us-Human
- https://www.gdcvault.com/play/1019353/Creating-the-AI-for-the

Ascension mapping: perception/memory/psychology are separate from the original physical action state. Search, combat and surrender emerge from those layers rather than replacing stage scripts.

## Runtime model

Each live character gets an external `HumanGuardState`. Nothing is added to the ROM-serialized `ChrRecord`, so no N64 layout is changed.

Persistent personality values:

- courage;
- aggression;
- discipline;
- perception;
- teamwork;
- nervousness;
- experience;
- squad role (`hold`, `advance`, `flank-left`, `flank-right`, `cover`).

Dynamic values:

- awareness (certainty about an intruder/target);
- fear;
- suppression;
- pain;
- confidence;
- attention;
- eye adaptation;
- danger memory;
- remembered position plus uncertainty radius.

The RNG is private to the module. It never calls GoldenEye's `randomGetNext()`, so simply enabling the overlay does not consume the original game's random stream.

## Continuous vision

The Human layer still uses `chrCanSeeBond()` for GoldenEye's actual STAN/object/door/character/path-blocker line of sight. The amount of awareness gained from a valid sample depends on:

1. distance versus the guard's script-owned baseline `visionrange`;
2. angular zone — strong central vision, progressively weaker peripheral recognition to the original ~110-degree side limit;
3. target movement;
4. STAN shade alpha as an experimental darkness proxy;
5. eye adaptation when looking from a brighter area into a darker target area;
6. current attention;
7. perception/experience personality;
8. current Human-AI intensity.

At high awareness the guard still waits a personality-dependent reaction delay (~0.18–1.1 seconds) before a Human-layer confirmation. At very close range GoldenEye's original detection safety remains available.

This is intentionally not "perfect realism": the lighting term is a proxy derived from data the original engine already has. A future renderer-backed luminance probe can replace it without changing the cognition model.

## Room-aware hearing

Classic GoldenEye uses a radial test roughly equivalent to `distance < hearingscale * noise * 100`. Human AI additionally builds a breadth-first shortest-hop map over `g_BgPortals` from Bond's current room and attenuates sounds at each room transition.

The current coefficients are conservative fixed portal losses. This already prevents the strongest form of "hearing through the entire building" while retaining cheap deterministic behaviour. A later version can read door openness/material metadata and give individual portals different attenuation.

Gunfire uses the real per-hand GoldenEye noise value. Player displacement is used as a deterministic footstep/movement-noise proxy.

Most importantly, hearing does **not** copy Bond's exact location. It creates an estimated point with an uncertainty radius based on distance, room hops, event type and guard experience, snaps that point back to a valid STAN, then feeds the approximate memory to the existing AI.

## Memory and search

Knowledge degrades rather than disappearing:

- direct sight sharply reduces uncertainty;
- sound produces a larger uncertain area;
- uncertainty grows while contact is lost;
- `dangerMemory` decays much more slowly than immediate awareness;
- confirmed guards search for roughly 14–24 seconds depending on discipline;
- search destinations are sampled inside the remembered uncertainty area and validated with `getposstan`;
- movement to a search point uses GoldenEye's own `plot_course_for_actor` and `ACT_GOPOS` pathing.

This creates the intended human failure mode: a guard can be correct about the general area and wrong about the exact room/position.

## Fear, suppression, pain and morale

Real damage raises pain, suppression and fear. Near misses raise suppression and fear even when no bullet hits — reusing GoldenEye's existing `numclosearghs`/near-miss behaviour. Nearby/adjacent-room character deaths create a longer-lived danger memory and fear response.

These values temporarily influence the existing ratings:

- suppression/pain/fear reduce effective accuracy;
- pain/suppression slightly reduce reaction/speed rating;
- a character with an existing non-zero grenade probability may become more or less willing to use it, but Human AI never grants grenades to a stage actor that did not already have permission;
- Human morale and awareness are blended into the existing `morale` and `alertness` bytes;
- extreme fear + suppression + low morale can invoke the original `chrTrySurrender` behaviour, except for civilians and invincible/script-protected characters.

## Communication without telepathy

A character with meaningful contact can share a degraded estimate with another armed non-civilian character in the same or an adjacent room. Highly team-oriented characters may pass a much weaker longer-range "radio" hint. The receiving actor never gets exact coordinates.

The overlay deliberately refuses to turn a completely zero-context character hostile merely because another slot is hostile. It transfers information into existing hearing/memory fields; the receiver's mission AI remains the authority on what that information means.

Speech assets are **not** synthesized by this module. The information-sharing system works mechanically; adding context-sensitive voiced barks is a separate content/localization task and should be built on top of the state transitions rather than hardcoded into cognition.

## Tactical behaviour and self-preservation

Human AI only requests a tactical movement when the original actor is stopped or patrolling. It does not interrupt bespoke attack/death/animation actions.

Depending on personality and pressure it can:

- advance using the original run-to-Bond primitive;
- select a left/right side waypoint for a flank;
- select a rear waypoint under high fear/suppression for self-preservation/cover;
- fall back to original sidestep/hop actions if a suitable waypoint is unavailable;
- search an uncertain remembered area after losing contact.

`AI.MaxTactical` prevents every guard from making an expensive repositioning decision at once. GoldenEye's original global active-guard/pathfinding budget remains in place as an additional safeguard.

## Reversibility

The overlay snapshots these per-character values before modifying them:

- `visionrange`;
- `hearingscale`;
- `accuracyrating`;
- `speedrating`;
- `arghrating`;
- `grenadeprob`;
- `morale`;
- `alertness`.

After each game frame, if a stage AI script changed one of these values away from the overlay's previous value, the new value becomes the baseline. This prevents Human AI from permanently overwriting mission-script decisions.

When F9 switches to Classic, all still-valid character slots are restored to their most recent script-owned baselines and the overlay becomes a no-op. Existing world consequences that already happened — a guard moved, an alarm was activated, a bullet was fired — are naturally not time-travelled away.

## Validation matrix

Before merging changes that tune Human AI, test at minimum:

| Scenario | Expected result |
|---|---|
| HumanMode=0 | identical Classic behaviour; module does no character writes |
| F9 Human -> Classic | parameter overlay restored immediately; game continues |
| long peripheral glimpse | awareness rises slowly; no instant omniscience |
| close frontal encounter | rapid recognition after short reaction latency |
| dark target / brighter guard | slower visual acquisition, then adaptation |
| silenced shot across rooms | much weaker/shorter propagation than same-room gunfire |
| loud shot | nearby connected-room guards become suspicious with uncertain location |
| lose line of sight | guard searches remembered area, uncertainty grows |
| near misses | suppression rises even without damage |
| wounded guard | temporary accuracy/reaction degradation |
| nearby casualty | fear/danger memory rises |
| high fear + low morale | eligible guard may surrender; bosses/civilians are protected |
| multiple guards | side/cover roles distribute movement; tactical cap respected |
| Facility scripted actors | objectives/action blocks remain authoritative |
| Cradle/Trevelyan | bespoke boss flow remains authoritative; no forced surrender |
| screenshot / frame dump | existing fast3d pre-swap hook still executes |
| Windows + Linux | both CI targets compile |

## Known limits / next research targets

1. Portal attenuation is currently fixed per hop; door state/material should become first-class acoustic data.
2. Lighting uses STAN shading as a proxy, not actual renderer luminance.
3. Casualty awareness uses room adjacency/proximity rather than a dedicated corpse line-of-sight query.
4. Communication has no new voiced barks yet.
5. The overlay deliberately avoids replacing stage AI lists; deeper squad planning should remain a policy layer over existing GE actions.
6. Boss and escort regressions need mission-by-mission playtesting because GoldenEye's local action blocks are as important as the global guard AI.
7. A debug visualizer should expose awareness, uncertainty circles, room sound hops, last-known position and selected tactical role in-game.

The guiding rule is **humanly plausible, not superhuman**: perception can be wrong, information can be stale, reactions take time, fear changes decisions, and coordination must come from observable/local communication rather than shared omniscience.
