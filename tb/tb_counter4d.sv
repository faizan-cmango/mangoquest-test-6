// TC-001: reset: count 0 after reset edges, from mid and max values (VPS-01, REQ-3.1.1, REQ-3.1.5)
// TC-002: hold: count stays 3 while en is 0 (VPS-02, REQ-3.1.4)
// TC-003: increment: en for one edge takes count 0 to 1 (VPS-03, REQ-3.1.2, REQ-3.1.8)
// TC-004: wrap: count 15 with en goes to 0 (VPS-04, REQ-3.1.3)
// TC-005: reset priority: rst_n 0 with en 1 gives 0 (VPS-05, REQ-3.1.6, REQ-3.1.1)
// TC-006: all values: 17 enabled edges visit 0 to 15 then 0 (VPS-06, REQ-3.1.2, REQ-3.1.3)
// TC-007: reset-to-idle: count at its reset value 0 after reset (REQ-3.1.1)
// TC-008: no X after reset: count is never X or Z once reset is applied (REQ-3.1.1)
// TC-009: no deadlock: count always changes within 16 enabled edges (REQ-3.1.2, REQ-3.1.3)
`default_nettype none
`timescale 1ns/1ps

module tb_counter4d;
  logic clk = 1'b0;
  logic rst_n = 1'b0;
  logic en = 1'b0;
  logic [3:0] count;

  integer cycle = 0;
  integer errors = 0;
  logic [3:0] exp_v;
  logic [15:0] seen_v = 16'h0;
  logic wrap_seen = 1'b0;
  integer k;

  counter4d dut (
      .clk  (clk),
      .rst_n(rst_n),
      .en   (en),
      .count(count)
  );

  always #5 clk = ~clk;
  always @(posedge clk) cycle <= cycle + 1;

  task automatic check(input string signal, input logic [63:0] expected, input logic [63:0] actual);
    if (actual !== expected) begin
      errors = errors + 1;
      $display("MISMATCH cycle=%0d signal=%s expected=%0h actual=%0h", cycle, signal, expected, actual);
    end
  endtask

  // Inputs change at the falling edge only (IDD R1, REQ-3.1.8); outputs sampled 1 ns after rise.
  task automatic step(input logic r, input logic e);
    @(negedge clk);
    rst_n = r;
    en = e;
    @(posedge clk);
    #1;
    if (!r) exp_v = 4'd0;
    else if (e) begin
      if (exp_v == 4'd15) wrap_seen = 1'b1;
      exp_v = exp_v + 4'd1;
    end
    check("count", {60'd0, exp_v}, {60'd0, count});
    if (^count === 1'bx) begin
      errors = errors + 1;
      $display("MISMATCH cycle=%0d signal=count_x expected=known actual=X", cycle);
    end
    seen_v[count] = 1'b1;
  endtask

  initial begin
    exp_v = 4'd0;
    // TC-001 / TC-007 / TC-008: reset applied first
    step(1'b0, 1'b0);
    check("count_reset", 64'd0, {60'd0, count});
    step(1'b0, 1'b0);
    // TC-003: increment
    step(1'b1, 1'b1);
    check("count_inc", 64'd1, {60'd0, count});
    // TC-002: hold at 3
    step(1'b1, 1'b1);
    step(1'b1, 1'b1);
    check("count_three", 64'd3, {60'd0, count});
    for (k = 0; k < 4; k = k + 1) step(1'b1, 1'b0);
    check("count_hold", 64'd3, {60'd0, count});
    // TC-005: reset beats en, from mid value
    step(1'b0, 1'b1);
    check("count_rst_en", 64'd0, {60'd0, count});
    step(1'b0, 1'b1);
    // TC-006 / TC-004 / TC-009: 17 enabled edges, includes the wrap
    for (k = 0; k < 17; k = k + 1) step(1'b1, 1'b1);
    check("count_wrap", 64'd1, {60'd0, count});
    check("coverage_values", 64'hFFFF, {48'd0, seen_v});
    check("coverage_wrap", 64'd1, {63'd0, wrap_seen});
    // TC-001: reset from max
    for (k = 0; k < 14; k = k + 1) step(1'b1, 1'b1);
    check("count_max", 64'd15, {60'd0, count});
    step(1'b0, 1'b0);
    check("count_rst_max", 64'd0, {60'd0, count});
    $display("DONE errors=%0d", errors);
    if (errors != 0) $fatal(1, "tb_counter4d failed");
    $finish;
  end
endmodule

`default_nettype wire
