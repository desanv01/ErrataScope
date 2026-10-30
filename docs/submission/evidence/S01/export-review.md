# ErrataScope interpretation review summary

- Document: ES0620 Rev 5
- Manufacturer: STMicroelectronics
- Source URL: https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf
- Source SHA-256: `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`
- Source authority: manufacturer
- Provenance: **Recorded live Nemotron result**
- Prompt version: `w04-draft-v5-grounded-no-thinking`
- Response hash: `4e62c49aaa01a61af4eda9031a9d71b6447c58396bc688e414a2e0679f26fa13`
- Provider request ID: 663823b4200b5f0a9cb78a2f092f5e71
- Model: nvidia/Nemotron-3.5-Super-VL
- Selected coverage: 2.2.18, 2.2.5
- Inventory complete: False

## Interpretation

> Provenance limitation: The preserved live response artifact is normalized JSON. The recorded response hash binds the original provider wire bytes; it cannot be re-derived from the normalized artifact. This limitation is retained rather than presenting a fabricated wire re-verification.

### 1. source_identity (supported)

ES0620 - Rev 5 - August 2026 www.st.com

- `st-es0620:ctx-identity` — page 1 (printed n/a), context; ES0620 - Rev 5 - August 2026 www.st.com

### 2. affected_revision (supported)

Section 2.2.5 Incorrect DBGMCU_IDCODE register value: Rev. Z = N (Limitation applicable. No workaround available), Rev. B = A (Limitation applicable. Workaround available), Rev. X = A (Limitation applicable. Workaround available)

- `st-es0620:p01:row-2-2-5` — page 2 (printed 2), 2.2.5; 2.2.5 | Incorrect DBGMCU_IDCODE register value | Rev. Z=N | Rev. B=A | Rev. X=A
- `st-es0620:ctx-legend-N` — page 2 (printed 2), context; N Limitation applicable. No workaround available
- `st-es0620:ctx-legend-A` — page 2 (printed 2), context; A Limitation applicable. Workaround available

### 3. consequence (supported)

The DBGMCU_IDCODE register value remains the same.

- `st-es0620:p06:s2.2.5:a002` — page 7 (printed 7), 2.2.5; The DBGMCU_IDCODE register value remains the same.

### 4. workaround_documented (supported)

For revision Z devices, no workaround is available. For revision B devices, use the new register definition Boot ROM (Base address: 0x1800 1000, Address offset: 0x0004).

- `st-es0620:p06:s2.2.5:a004` — page 7 (printed 7), 2.2.5; For revision Z devices, no workaround is available.
- `st-es0620:p06:s2.2.5:a005` — page 7 (printed 7), 2.2.5; For revision B devices, use the new register definition Boot ROM (Base address: 0x1800 1000, Address
- `st-es0620:p06:s2.2.5:a006` — page 7 (printed 7), 2.2.5; offset: 0x0004).

### 5. affected_revision (supported)

Section 2.2.18 Incorrect reset behavior when using NRST pin: Rev. Z = A (Limitation applicable. Workaround available), Rev. B = A (Limitation applicable. Workaround available), Rev. X = - (Limitation not applicable)

- `st-es0620:p01:row-2-2-18` — page 2 (printed 2), 2.2.18; 2.2.18 | Incorrect reset behavior when using NRST pin | Rev. Z=A | Rev. B=A | Rev. X=-
- `st-es0620:ctx-legend-A` — page 2 (printed 2), context; A Limitation applicable. Workaround available
- `st-es0620:ctx-legend--` — page 2 (printed 2), context; - Limitation not applicable.

### 6. trigger_condition (supported)

Using the NRST pin for reset.

- `st-es0620:p09:s2.2.18:a002` — page 10 (printed 10), 2.2.18; The system may fail to perform a correct reset when using the NRST pin. This issue might require a full power
- `st-es0620:p09:s2.2.18:a005` — page 10 (printed 10), 2.2.18; When using the NRST pin, configure the reset mode to power-on reset as follows:

### 7. consequence (supported)

The system may fail to perform a correct reset when using the NRST pin. This issue might require a full power cycle (power off and on) to restore functionality.

- `st-es0620:p09:s2.2.18:a002` — page 10 (printed 10), 2.2.18; The system may fail to perform a correct reset when using the NRST pin. This issue might require a full power
- `st-es0620:p09:s2.2.18:a003` — page 10 (printed 10), 2.2.18; cycle (power off and on) to restore functionality.

### 8. workaround_documented (supported)

When using the NRST pin, configure the reset mode to power-on reset: 1. On the first system power-on reset, set the reset type to power-on reset by setting the CORE_RESET_TYPE bit in the SYSCFG_CM55RSTCR register. 2. Generate a software reset by setting the SYSRESETREQ bit in the AIRCR register of the SBC. In the main application code, declare a global variable at any address in AXISRAM1; at the start of main, if the variable is not 0x11223344, set it to 0x11223344, enable SYSCFG clock, set power-on reset from NRST pin in SYSCFG->CM55RSTCR, issue __ISB() and __DSB(), then call NVIC_SystemReset().

- `st-es0620:p09:s2.2.18:a005` — page 10 (printed 10), 2.2.18; When using the NRST pin, configure the reset mode to power-on reset as follows:
- `st-es0620:p09:s2.2.18:a006` — page 10 (printed 10), 2.2.18; 1. On the first system power-on reset, set the reset type to power-on reset by setting the CORE_RESET_TYPE
- `st-es0620:p09:s2.2.18:a007` — page 10 (printed 10), 2.2.18; bit in the SYSCFG_CM55RSTCR register.
- `st-es0620:p09:s2.2.18:a008` — page 10 (printed 10), 2.2.18; 2. Generate a software reset by setting the SYSRESETREQ bit in the AIRCR register of the SBC.
- `st-es0620:p09:s2.2.18:a009` — page 10 (printed 10), 2.2.18; In the main application code, declare this global variable at any address in AXISRAM1:
- `st-es0620:p09:s2.2.18:a010` — page 10 (printed 10), 2.2.18; volatile uint32_t * init_p = (volatile uint32_t *) 0x34001004;
- `st-es0620:p09:s2.2.18:a011` — page 10 (printed 10), 2.2.18; At the start of the main function, insert:
- `st-es0620:p09:s2.2.18:a012` — page 10 (printed 10), 2.2.18; /* Enable SYSCFG Clock */
- `st-es0620:p09:s2.2.18:a013` — page 10 (printed 10), 2.2.18; RCC->APB4ENSR2 |= 1; // SYSCFGEN: SYSCFG enable in RCC_APB4HENR register
- `st-es0620:p09:s2.2.18:a014` — page 10 (printed 10), 2.2.18; if(*init_p != 0x11223344) //First power-on reset is detected
- `st-es0620:p09:s2.2.18:a015` — page 10 (printed 10), 2.2.18; {
- `st-es0620:p09:s2.2.18:a016` — page 10 (printed 10), 2.2.18; *init_p=0x11223344; // change init_p variable with a known value
- `st-es0620:p09:s2.2.18:a017` — page 10 (printed 10), 2.2.18; SYSCFG->CM55RSTCR |= 1; //Setting power-on reset from NRST pin
- `st-es0620:p09:s2.2.18:a018` — page 10 (printed 10), 2.2.18; __ISB(); // Instruction Synchronization Barrier
- `st-es0620:p09:s2.2.18:a019` — page 10 (printed 10), 2.2.18; __DSB(); // Data Synchronization Barrier
- `st-es0620:p09:s2.2.18:a020` — page 10 (printed 10), 2.2.18; NVIC_SystemReset(); // Generate a system reset
- `st-es0620:p09:s2.2.18:a021` — page 10 (printed 10), 2.2.18; }

### 9. workaround_restriction (supported)

The example code declares the global variable at address 0x34001004, but the prose states the variable may be declared at any address in AXISRAM1; the specific address is not required.

- `st-es0620:p09:s2.2.18:a009` — page 10 (printed 10), 2.2.18; In the main application code, declare this global variable at any address in AXISRAM1:
- `st-es0620:p09:s2.2.18:a010` — page 10 (printed 10), 2.2.18; volatile uint32_t * init_p = (volatile uint32_t *) 0x34001004;

## Unresolved fields

affected_device, exception

## Review history

- Revision 1: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:22:32.029881+00:00 — Source excerpts checked; unresolved fields remain visible.
- Revision 2: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:22:32.241685+00:00 — External concurrency check.
- Revision 3: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:23:23.203864+00:00 — Source excerpts checked; unresolved fields remain visible.
- Revision 4: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:23:23.337210+00:00 — External concurrency check.
- Revision 5: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:23:34.439902+00:00 — Source excerpts checked; unresolved fields remain visible.
- Revision 6: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:23:34.599105+00:00 — External concurrency check.
- Revision 7: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:24:56.024867+00:00 — Source excerpts checked; unresolved fields remain visible.
- Revision 8: **reviewed** by 00000000-0000-0000-0000-000000000065 at 2026-10-30 11:24:56.173959+00:00 — External concurrency check.

## Known limitations

- Selected entries only; document inventory is not complete.
- A reviewed interpretation is human acknowledgement, not an accepted executable rule.
- No applicability assessment, fact editing or VerifForge execution is included.
- Historical wire-byte hashes cannot be re-derived from normalized response artifacts.

A reviewed interpretation is not an accepted executable rule.
