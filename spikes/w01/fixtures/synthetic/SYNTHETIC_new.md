SYNTHETIC FIXTURE — NOT A MANUFACTURER DOCUMENT

Fixture ID: SYNTH-PAIR-NEW
Fixture version: NEW
Authored: 2026-10-29 by the W01 worker for change-detection fixture testing only.
Device: fictional "ACME SYNTH-1" microcontroller. Not a real product. No real
manufacturer revision is asserted or implied anywhere in this file.

Errata sheet SYNTH-ES-0001, Rev B (fixture-new)

2.1 I2C clock stretching timeout
Description
A clock stretching timeout occurs when the I2C bus is clocked above 1 MHz in
fast mode.
Workaround
Limit the I2C bus clock to 1 MHz in fast mode.

2.2 Debug port lockup after warm reset
Description
The debug port remains locked after a warm reset.
Workaround
None.

2.3 Reset pulse shorter than 20 ns is ignored
Description
A pulse on the NRST pin shorter than 20 ns is ignored, so no reset occurs.
Workaround
Hold the NRST pin low for at least 1 us.
