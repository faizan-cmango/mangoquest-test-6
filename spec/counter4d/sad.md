# System Architecture Document — counter4d · SAD v0.1

> Machine index: `sad.yaml`. Requirements live in `rtm.yaml`, ports in `idd/`, scenarios in
> `vps.yaml`, risk in `riskmap.yaml`, clocks in `clocks.yaml`.

## 1 Scope and context
counter4d is a 4-bit wrapping up-counter with enable and synchronous reset, on one clock. It sits on an evaluation board (brs.yaml).
Out of scope: registers or bus interfaces, interrupts, clock-domain crossings, power management, memories, clock gating. Scan ports are added later by DFT insertion.
Assumptions: the interface is final; no area target (ADR-02); IDD of class level (ADR-01); board currents chosen by me (ADR-03); count undefined before the first reset edge (ADR-04).

## 2 Block decomposition
One block, counter4d, owned by Kemi. No split is useful.

## 3.1 Counter behaviour — REQ-3.1.1 … REQ-3.1.8
At each rising clk edge: reset (REQ-3.1.1, REQ-3.1.6) beats increment (REQ-3.1.2, REQ-3.1.3), which beats hold (REQ-3.1.4). Outputs change only at the clock edge (REQ-3.1.5). Ports are fixed by REQ-3.1.7. The harness drives inputs only at falling edges and starts the clock low (IDD-CTRL R1); it is reused unchanged on the gate-level netlist.
Sketch: en=1 at edges e1,e2 gives count n, n+1, n+2.

## 6 Performance power and area
Timing target REQ-3.1.8 at the clock of clocks.yaml. Feasibility (proxy RTL, opensta_liberty, confidence 0.5, tt, pre-layout): fmax estimate 1257.9 MHz, area 140.1 um2, target met.

## 7 Risk register
See `riskmap.yaml`.

## 8 Open items
No open ArchChallenge. Open: Device Models for the chip and the 1.8 V regulator, and the parts snapshot, to be supplied by a person (BRS-9).
