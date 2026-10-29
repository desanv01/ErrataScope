SYNTHETIC FIXTURE — NOT A MANUFACTURER DOCUMENT

Fixture ID: SYNTH-PAIR-OLD
Fixture version: OLD
Authored: 2026-10-29 by the W01 worker for change-detection fixture testing only.
Device: fictional "ACME SYNTH-1" microcontroller. Not a real product. No real
manufacturer revision is asserted or implied anywhere in this file.

Errata sheet SYNTH-ES-0001, Rev A (fixture-old)

2.1 I2C clock stretching timeout
Description
A clock stretching timeout occurs when the I2C bus is clocked above 400 kHz.
Workaround
Limit the I2C bus clock to 400 kHz.

2.2 Debug port lockup after warm reset
Description
The debug port remains locked after a warm reset.
Workaround
None.
