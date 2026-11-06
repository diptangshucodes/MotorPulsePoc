# MotorPulse AI: leadership video prompt and storyboard

This video brief is based on [MOTORPULSE_PROJECT_BRIEF.md](./MOTORPULSE_PROJECT_BRIEF.md). It is designed to be supplied to a video-generation model, motion-design team, or production partner. It presents a compelling leadership story while clearly distinguishing the current proof of concept from a future, instrumented pilot.

## Video-generation prompt

Create a polished, leadership-level animated concept video introducing **MotorPulse AI**, an edge-first predictive-maintenance proof of concept for industrial motors and other rotating assets. Target a total runtime of **1 minute 50 seconds** (110 seconds), with an absolute maximum of 2 minutes.

### Audience and objective

The audience is senior operations, manufacturing, reliability, and technology leadership. The objective is to make the operational problem tangible by showing a motor failure, a stopped line, reactive maintenance, and the resulting high bill; then show the proposed workflow, communicate a transparent Ontario facility scenario, and invite support for a measured pilot. The video should feel credible and practical—not like a speculative AI advertisement.

### Narrative arc

Open on a specific, believable failure story: a bearing begins to deteriorate, vibration and heat rise, the motor fails, and a production line stops. Show the real operational consequences visually: an urgent maintenance callout, a rushed repair, production contribution at risk, and an emergency repair invoice that is larger than a planned repair would have been. Use the ten-motor scenario's actual arithmetic to make the high bill concrete, but label it visibly as an illustrative model—not a real incident, customer invoice, or Ontario-wide statistic. Then show how MotorPulse AI could help maintenance teams detect a change, investigate it, and plan work earlier. End with a focused read-only pilot and a clear request to validate results before scaling.

### Visual direction

- Modern industrial motion graphics: real-looking motors, pumps, conveyor drives, a clean factory floor, and close-up technical visualization of vibration.
- A polished enterprise palette: deep navy, white, cool light gray, teal, cyan, and restrained amber/red for abnormal conditions.
- Camera movement should be deliberate and calm: smooth tracking, measured push-ins, and clean match cuts.
- Use a simple recurring signal-wave motif that travels from the physical motor through the edge system to a human-reviewed maintenance action.
- Make the failure sequence visually specific: bearing vibration worsens, heat rises, a motor trips or stops, the conveyor or production line stops, output backs up, an operator calls maintenance, and an urgent repair is arranged. Communicate a believable operational disruption, not a spectacular accident.
- Put the cost on screen as an accumulating, itemized illustrative bill: 8 hours of stopped production x CAD $1,500/hour = CAD $12,000 contribution at risk; emergency repair CAD $4,500 versus planned repair CAD $850 = CAD $3,650 incremental repair premium; modeled total exposure per event = CAD $15,650. Then show 2.4 expected events/year across the hypothetical ten-motor facility, yielding CAD $37,560/year modeled exposure. Label every figure as a modeled scenario, not an actual failure or bill.
- Stamp any emergency-repair invoice `ILLUSTRATIVE SCENARIO — NOT A CUSTOMER INVOICE`. Keep the full CAD $4,500 emergency repair bill distinct from its CAD $3,650 premium over planned repair.
- Establish Ontario/Canada subtly with a location tag or small maple-leaf cue. Do not use disaster imagery or imply the province has a quantified motor-failure loss total.
- The MotorPulse AI logo should be original and minimal: motor/bearing outline with a pulse waveform. If no approved logo file is supplied, use a clean text treatment rather than inventing a complex brand mark.
- Use dashboard visuals only as a **prototype/demo interface**. Prefer cropped, legible shots; label simulated screens as “DEMO DATA” or “CONCEPT UI.”
- Avoid cyberpunk styling, floating brain graphics, robots taking over, fake customer testimonials, or unverified production footage represented as a real customer site.

### Truth and claims rules

The proposed story may show sensor-to-edge-to-dashboard architecture, but must not imply all components are connected today. A small production-stage label can say “PROOF OF CONCEPT” or “PILOT PATH.”

The financial figures below are **modeled assumptions for a hypothetical 10-motor Ontario facility**, not measured results, not an Ontario-wide total, and not a promise. The breakdown visualizes a representative modeled event; it is not footage or a report of a real failure:

- CAD $12,000 production contribution at risk for one 8-hour stop, at the assumed CAD $1,500 per hour.
- CAD $4,500 emergency repair invoice compared with CAD $850 for planned repair; the modeled incremental premium is CAD $3,650.
- CAD $15,650 modeled exposure per event: CAD $12,000 + CAD $3,650.
- 2.4 expected events/year for the scaled 10-motor scenario, producing the annual figures below.
- $37,560 annual modeled failure-cost exposure.
- $11,268 gross opportunity at a 30% early-planning scenario.
- 5.76 hours (about 5.8 hours) of potential production capacity recovered per year under the same scenario.

Show the key assumptions where practical: 2.4 expected events/year (scaled from 6 events/year across 25 motors), 8 hours/event, CAD $1,500 contribution at risk per downtime hour, CAD $4,500 emergency repair, CAD $850 planned repair, and a CAD $3,650 incremental repair premium per event. Make clear that the gross opportunity is before system costs, assumes recovered production can be sold, and excludes energy and labor savings. Do not call it net savings or ROI.

Ontario real GDP growth of 1.6% in 2023 may appear only as clearly labeled **regional economic context**, with a Statistics Canada citation. Never present it as a failure-cost or predictive-maintenance statistic. The production may omit this detail if it distracts from the main story.

Describe the existing edge-AI implementation accurately: it is a statistical detector that compares vibration-window features with a motor-specific healthy baseline. It is not a validated fault classifier, remaining-life model, or safety system. The current dashboard uses seeded and simulated demo data; the current ESP32/Wokwi example sends a button event, not sensor readings. Do not depict an actual connected production line or claim measured predictive accuracy.

### Audio

Use a confident, warm, measured executive narrator. The delivery should be grounded, human, and optimistic, with a neutral Canadian or broadly North American English accent. Avoid breathless sales language, fear-based music, or exaggerated urgency.

Use restrained cinematic electronic music: subtle industrial pulse at the opening, slightly tense but not ominous during failure, then a composed and optimistic lift as the workflow and pilot plan appear. Keep the voice-over clear and dominant. Add light sound design for motor hum, signal pulse, alert transition, and a work-order confirmation; do not make alarms dramatic.

Use concise on-screen labels and clean kinetic typography. Generate all labels as post-production text overlays rather than relying on AI-generated lettering. Include accurate captions/subtitles.

## Storyboard and timed narration

**Target runtime: 1:50 (110 seconds). The first 50 seconds must clearly show the failure and high-bill problem before revealing the solution.**

| Time | Picture and animation | On-screen text | Voice-over |
|---|---|---|---|
| 00:00-00:10 | Start in the middle of a normal production shift. A conveyor feeds product while a motor-driven pump runs steadily. Show a small `ONTARIO FACILITY — DRAMATIZATION` label; do not imply this is a real customer site. | `ONTARIO FACILITY — DRAMATIZATION` / `One critical motor. One production line.` | “A production line is running to schedule. Then one critical motor starts to change.” |
| 00:10-00:25 | Close-up on a bearing housing. Vibration trace grows uneven; the housing warms; a subtle warning light appears. The motor begins to rattle, then trips. Keep the event realistic and safe—no explosion, injury, or flying parts. | `Vibration rising` / `Temperature rising` / `Motor failure` | “A bearing wears. Vibration rises. Heat follows. Before the next scheduled check, the motor fails—and the line goes quiet.” |
| 00:25-00:38 | Show the conveyor stop, product backing up, an operator alerting maintenance, and a technician called in. A rushed parts search and schedule board show a delayed production order. Convey operational pressure with restrained sound and graphics. | `Unplanned stop` / `Emergency callout` / `Production delayed` | “Output stops. Orders fall behind. Maintenance is called in urgently, parts have to be found, and a repair that could have been planned becomes an interruption.” |
| 00:38-00:50 | Show a clearly fictional, itemized bill building on screen beside the stopped line. Reveal the arithmetic one line at a time; visually distinguish the full emergency repair invoice from its incremental premium over planned maintenance. | `ILLUSTRATIVE SCENARIO — NOT A CUSTOMER INVOICE` / `8 h x $1,500/h = $12,000 contribution at risk` / `$4,500 emergency repair vs. $850 planned repair` / `$3,650 repair premium` / `$15,650 modeled exposure for this event` | “In our illustrative case, eight hours puts twelve thousand dollars of production contribution at risk. The emergency repair costs forty-five hundred dollars, versus eight hundred fifty if planned. That is fifteen thousand six hundred fifty dollars of modeled exposure for one event.” |
| 00:50-01:03 | Pull back from the single stopped line into a 10-motor facility schematic. Count 2.4 expected annual events into the scenario card and show the annual exposure. Stamp `MODELED — NOT ONTARIO-WIDE DATA`. | `10-motor facility scenario` / `2.4 modeled events/year` / `$37,560 annual exposure*` / `Assumptions shown; site data required` | “Scaled across a hypothetical ten-motor facility, the stated assumptions produce thirty-seven thousand five hundred sixty dollars of modeled annual exposure—not an Ontario-wide loss statistic.” |
| 01:03-01:16 | Reveal MotorPulse AI. Show an illustrative sensor on a motor, then a clearly labeled concept path to ESP32, Wi-Fi, local MQTT, Raspberry Pi edge service, and a `CONCEPT UI` dashboard. Use dashed connectors to signal a proposed integration path. | `MotorPulse AI` / `SENSE  →  DETECT  →  PLAN` / `Proof-of-concept architecture` | “MotorPulse AI is our proof of concept for acting earlier: sense each asset, learn its healthy baseline, and flag a meaningful change close to the equipment.” |
| 01:16-01:31 | Animate the edge detector comparing healthy and changed vibration windows. A demo fleet tile changes to warning. A technician reviews the anomaly explanation, inspects the motor during a planned window, and records the outcome. | `Baseline comparison` / `Anomaly detected` / `Technician reviews and plans` / `DEMO DATA` | “A lightweight edge service compares vibration features with a motor-specific baseline. The dashboard makes a change visible so a technician can investigate and plan the work—not blindly trust an automated diagnosis.” |
| 01:31-01:41 | Return to the scenario, now showing the line being serviced during a planned window. Display the gross opportunity range with clear disclaimers; do not animate all of it as guaranteed cash in a bank account. | `20-40% planning sensitivity` / `$7,512-$15,024 gross opportunity*` / `30% case: $11,268` / `Before system costs; not net savings` | “If earlier planning avoids some disruption, the thirty-percent scenario suggests eleven thousand two hundred sixty-eight dollars in gross opportunity. It is a hypothesis to validate—not a promise.” |
| 01:41-01:50 | Close on two pilot motors, a read-only checklist, then the MotorPulse AI title and presenter name if approved. Fade to a clean factory silhouette. | `Start with 2 critical motors` / `Instrument. Run read-only. Verify. Scale on evidence.` / `MotorPulse AI — Sense. Detect. Plan.` | “Start with two critical motors. Verify with technicians and site records. Then scale what works. MotorPulse AI. Sense. Detect. Plan.” |

### Failure-and-loss visual direction

The audience should see the cause-and-effect chain—not just hear about it:

1. A bearing begins to degrade; vibration and temperature traces rise.
2. The motor fails or trips; the production line visibly stops.
3. Output backs up; a maintenance callout, urgent parts search, and schedule disruption follow.
4. An itemized illustrative bill clearly separates lost production contribution from the emergency-repair premium.
5. The annual 10-motor scenario then scales the same assumptions transparently.

Use the phrase `ILLUSTRATIVE SCENARIO — NOT A CUSTOMER INVOICE` on the bill. Do not use a fabricated company logo, real company name, purported real incident footage, or an unexplained dollar amount. The dramatized failure is a representative story; the arithmetic is a hypothetical scenario derived from the project assumptions.

## Complete voice-over script

> A production line is running to schedule. Then one critical motor starts to change.
>
> A bearing wears. Vibration rises. Heat follows. Before the next scheduled check, the motor fails—and the line goes quiet.
>
> Output stops. Orders fall behind. Maintenance is called in urgently, parts have to be found, and a repair that could have been planned becomes an interruption.
>
> In our illustrative case, eight hours puts twelve thousand dollars of production contribution at risk. The emergency repair costs forty-five hundred dollars, versus eight hundred fifty if planned. That is fifteen thousand six hundred fifty dollars of modeled exposure for one event.
>
> Scaled across a hypothetical ten-motor facility, the stated assumptions produce thirty-seven thousand five hundred sixty dollars of modeled annual exposure—not an Ontario-wide loss statistic.
>
> MotorPulse AI is our proof of concept for acting earlier: sense each asset, learn its healthy baseline, and flag a meaningful change close to the equipment.
>
> A lightweight edge service compares vibration features with a motor-specific baseline. The dashboard makes a change visible so a technician can investigate and plan the work—not blindly trust an automated diagnosis.
>
> If earlier planning avoids some disruption, the thirty-percent scenario suggests eleven thousand two hundred sixty-eight dollars in gross opportunity. It is a hypothesis to validate—not a promise.
>
> Start with two critical motors. Verify with technicians and site records. Then scale what works. MotorPulse AI. Sense. Detect. Plan.

## Required end card / source note

Keep the final frame simple. Use the approved MotorPulse AI logo and, if desired, the portrait and exact name **Diptangshu Dolui**. Include a small but legible note in the video description or closing credits:

> Financial figures are illustrative assumptions for a hypothetical 10-motor facility, scaled from the MotorPulse AI internal client-projection scenario. They are not measured customer results, Ontario-wide failure costs, net savings, or a guarantee. Site data and implementation costs are required to validate value.

If the video includes Ontario GDP context, cite:

> Statistics Canada, “Gross domestic product by industry: Provinces and territories, 2023,” released May 1, 2024. https://www150.statcan.gc.ca/n1/daily-quotidien/240501/dq240501a-eng.htm

## Production and review checklist

- Runtime is 110 seconds or less than 2 minutes.
- Voice-over matches the storyboard timing and remains easy to understand.
- All financial figures are labeled modeled and hypothetical.
- The video visibly shows the motor failure, line stoppage, urgent callout, production disruption, and itemized high-bill scenario before revealing MotorPulse AI.
- The displayed emergency repair bill is marked `ILLUSTRATIVE SCENARIO — NOT A CUSTOMER INVOICE`; the CAD $4,500 full repair bill is not confused with the CAD $3,650 premium over planned repair.
- The per-event calculation is internally consistent: CAD $12,000 production contribution at risk + CAD $3,650 repair premium = CAD $15,650 modeled exposure.
- The visual does not imply $37,560 or $11,268 is measured provincial data or actual customer savings.
- Gross opportunity is not described as net savings, ROI, or guaranteed payback.
- Simulated app values are marked as demo/concept visuals.
- The animation does not imply sensors, MQTT, the edge API, and dashboard are already integrated end-to-end.
- No invented customer name, testimonial, validated accuracy, fault probability, or failure prediction is presented as fact.
- The pilot is positioned as read-only and human-reviewed; no automated motor control or safety function is implied.
- Figures, labels, logo, citations, captions, and name are checked in post-production for spelling and legibility.
