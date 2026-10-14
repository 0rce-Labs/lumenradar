# Scope boundary — please read before opening a feature request

LumenRadar is **detection-only** tooling. It exists to analyze camera footage
for covert optical signaling. It will never:

- modulate a screen, LED, or keyboard backlight to carry a message,
- capture screen content or input to generate answers,
- integrate an LLM or any answer-generation path,
- add an "application API" that pairs a beacon with content capture.

The calibration beacon (`lumenradar beacon`) is a fixed-pattern dataset
labeling utility for the defender's own hardware — wiring it into anything
else is out of scope by design. See `docs/THREAT-MODEL.md`.

Pull requests adding transmission/encoding of messages via screen/LED
channels will be rejected without review.
