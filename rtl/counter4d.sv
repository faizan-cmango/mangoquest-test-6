// -- A · HEADER ------------------------------------------------------------------------
// Module  : counter4d              File: counter4d.sv
// Project : counter4d
// SAD     : 3.1                    Risk: LOW
// REQ-IDs : REQ-3.1.1, REQ-3.1.2, REQ-3.1.3, REQ-3.1.4, REQ-3.1.5, REQ-3.1.6, REQ-3.1.7,
//           REQ-3.1.8
// Author  : Kemi (RTL Design), rev 1.0
// PREFIXES: cnt
// nosplit : single 4-bit register, no FSM states, so no control/datapath split
// PURPOSE : 4-bit wrapping up-counter with enable and synchronous active-low reset on clk.
// DEBUG NOTES : probe in this order: rst_n, en, cnt_value_next, cnt_value_ff, count.
//   Waveform recipe: add wave cnt_*   then  add wave count
// KNOWN GOTCHAS : count is X until the first rising edge with rst_n low (ADR-04); reset
//   is synchronous, so it takes effect only at a rising clk edge (REQ-3.1.5).
`default_nettype none
`timescale 1ns/1ps

module counter4d (
    // -- B · PARAMETERS AND PORTS --------------------------------------------------------
    input  wire logic       clk,    // REQ-3.1.5 100 MHz clock
    input  wire logic       rst_n,  // REQ-3.1.1 synchronous active-low reset
    input  wire logic       en,     // REQ-3.1.2 count enable
    output logic      [3:0] count   // REQ-3.1.2 REQ-3.1.7 counter value
);

  // -- C · DECLARATIONS — SAD 3.1 ----------------------------------------------------------
  logic [3:0] cnt_value_ff;    // REQ-3.1.1 REQ-3.1.2 REQ-3.1.5 counter register
  logic [3:0] cnt_value_next;  // REQ-3.1.1 REQ-3.1.2 REQ-3.1.3 REQ-3.1.4 REQ-3.1.6 next value

  // -- D · COMBINATIONAL — SAD 3.1 ---------------------------------------------------------
  // .. cnt : next value, increment beats hold — REQ-3.1.2, REQ-3.1.3, REQ-3.1.4
  assign cnt_value_next = en ? cnt_value_ff + 4'd1 : cnt_value_ff;

  // -- E · SEQUENTIAL — SAD 3.1 ------------------------------------------------------------
  // .. cnt : counter register, reset beats en — REQ-3.1.1, REQ-3.1.5, REQ-3.1.6, REQ-3.1.8
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      cnt_value_ff <= '0;
    end else begin
      cnt_value_ff <= cnt_value_next;
    end
  end

  // -- F · ASSERTIONS AND DEBUG HOOKS — SAD 3.1 --------------------------------------------
`ifndef SYNTHESIS
  always @(posedge clk) begin
    if (rst_n && en && (cnt_value_ff == 4'd15)) begin
      assert (cnt_value_next == 4'd0) else $error("a_cnt_wrap");
    end
  end
`endif

  // -- G · OUTPUTS — SAD 3.1 ---------------------------------------------------------------
  assign count = cnt_value_ff;  // REQ-3.1.2 REQ-3.1.7

endmodule

`default_nettype wire
