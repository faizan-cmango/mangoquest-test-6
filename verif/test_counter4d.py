# ==== A. Header ===================================================================
# Testbench:     tb_counter4d (cocotb)
# Project:       counter4d
# SAD:           spec/counter4d, section 3.1
# Risk:          LOW: line, branch, toggle, FSM and functional 100 %
# Testplan:      verif/counter4d/testplan.yaml @v1.0
# Author:        Dayo
# PURPOSE:       One directed test per VPS scenario and one seeded random test; a monitor
#                feeds every rising edge to a scoreboard built on a model of REQ-3.1.1 to REQ-3.1.6.
# DEBUG NOTES:   Read the first MISMATCH line. Add to the waveform, in order: rst_n, en, count.
# KNOWN GOTCHAS: Inputs change only after a falling edge (IDD-CTRL R1); the clock starts low.
#                count is X until the first reset edge (ADR-04): checks start after it.
"""cocotb harness skeleton for counter4d."""

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge
from cocotb_coverage.coverage import CoverPoint, coverage_db

# ==== B. Interface layer ==========================================================
CLK_PERIOD_NS = 10  # clocks.yaml: clk at 100 MHz
RESET_EDGES = 2  # VPS-01: rst_n held 0 for two rising edges (REQ-3.1.1)
CNT_MAX = 15  # REQ-3.1.3: the value that wraps
RANDOM_EDGES = 400  # testplan constraint_model: a few hundred edges
RESET_PROB = 0.05  # testplan constraint_model IDD-CTRL rst_n: about 1 edge in 20
RESET_MAX_EDGES = 3  # testplan constraint_model IDD-CTRL rst_n: 1 to 3 edges
EN_PROB = 0.75  # testplan constraint_model IDD-CTRL en: 3 edges in 4 high
LOG = logging.getLogger("tb_counter4d")


@dataclass(frozen=True)
class CntSample:
    """One rising edge: the inputs it acted on and count after it."""

    rst_n: int
    en: int
    count: int


def cnt_read(handle, name: str) -> int:
    """A port's value as an int; X or Z is a failure (MQ-TBS-004)."""
    value = handle.value
    if not value.is_resolvable:
        raise AssertionError(f"UNKNOWN signal={name} observed={value}")
    return int(value)


class CntDriver:
    """Drives en and rst_n after the falling edge only (IDD-CTRL R1)."""

    def __init__(self, dut) -> None:
        self.clk = dut.clk
        self.en = dut.en

    def power_up(self) -> None:
        self.en.value = 0

    async def drive(self, en: int) -> None:
        await FallingEdge(self.clk)
        self.en.value = en


class CntMonitor:
    """Observes count after every rising edge. It only observes."""

    def __init__(self, dut, on_sample: Callable[[CntSample], None]) -> None:
        self.dut = dut
        self.on_sample = on_sample

    async def run(self) -> None:
        dut = self.dut
        while True:
            await RisingEdge(dut.clk)
            rst_n = cnt_read(dut.rst_n, "rst_n")
            en = cnt_read(dut.en, "en")
            await ReadOnly()
            if not rst_n or self.on_sample.__self__.started:
                self.on_sample(CntSample(rst_n, en, cnt_read(dut.count, "count")))


class CntReset:
    """rst_n: synchronous, active low (clocks.yaml); held RESET_EDGES edges."""

    def __init__(self, dut) -> None:
        self.clk = dut.clk
        self.rst_n = dut.rst_n

    def power_up(self) -> None:
        self.rst_n.value = 0

    async def assert_reset(self) -> None:
        await FallingEdge(self.clk)
        self.rst_n.value = 0

    async def release(self, edges: int = RESET_EDGES) -> None:
        for _ in range(edges):
            await RisingEdge(self.clk)
        await FallingEdge(self.clk)
        self.rst_n.value = 1


# ==== C. Stimulus =================================================================
class CntEnv:
    """One test's harness: components, model and coverage, one seed."""

    def __init__(self, dut, test: str) -> None:
        self.seed = cocotb.RANDOM_SEED
        self.rng = random.Random(self.seed)
        LOG.info("SEED=%d test=%s harness=tb_counter4d dut=counter4d", self.seed, test)
        self.dut = dut
        self.driver = CntDriver(dut)
        self.reset = CntReset(dut)
        self.scoreboard = CntScoreboard(test, self.seed)
        self.scoreboard.listeners.append(cnt_cov_sample)
        self.monitor = CntMonitor(dut, self.scoreboard.observe)

    async def start(self) -> None:
        self.reset.power_up()
        self.driver.power_up()
        Clock(self.dut.clk, CLK_PERIOD_NS, unit="ns").start(start_high=False)
        cocotb.start_soon(self.monitor.run())
        await self.reset.release()

    async def enable(self, edges: int) -> None:
        """en 1 for `edges` rising edges, then en 0."""
        for _ in range(edges):
            await self.driver.drive(1)
        await self.driver.drive(0)

    async def idle(self, edges: int) -> None:
        for _ in range(edges):
            await self.driver.drive(0)

    def finish(self, vps: str, at_least: int) -> None:
        checked = self.scoreboard.checked.get(vps, 0)
        assert checked >= at_least, f"{vps}: {checked} checks ran, {at_least} expected"
        coverage_db.export_to_xml(filename="coverage.xml")


@cocotb.test(timeout_time=20, timeout_unit="us")
async def test_vps_01_reset(dut) -> None:
    """VPS-01: reset at power-up and from zero, mid and max."""
    env = CntEnv(dut, "test_vps_01_reset")
    await env.start()
    # skeleton: reset from count 0, 5 and 15, two edges each (waits for the RTL)
    env.finish("VPS-01", 2 * RESET_EDGES)


@cocotb.test(timeout_time=20, timeout_unit="us")
async def test_vps_02_hold(dut) -> None:
    """VPS-02: en 0 holds count at 3."""
    env = CntEnv(dut, "test_vps_02_hold")
    await env.start()
    # skeleton: enable 3 edges, idle 5 edges (waits for the RTL)
    env.finish("VPS-02", 5)


@cocotb.test(timeout_time=20, timeout_unit="us")
async def test_vps_03_increment(dut) -> None:
    """VPS-03: one enabled edge from 0 and from a mid value."""
    env = CntEnv(dut, "test_vps_03_increment")
    await env.start()
    # skeleton: one enabled edge from 0, then from 7 (waits for the RTL)
    env.finish("VPS-03", 2)


@cocotb.test(timeout_time=20, timeout_unit="us")
async def test_vps_04_wrap(dut) -> None:
    """VPS-04: 15 to 0 on an enabled edge."""
    env = CntEnv(dut, "test_vps_04_wrap")
    await env.start()
    # skeleton: 16 enabled edges (waits for the RTL)
    env.finish("VPS-04", 1)


@cocotb.test(timeout_time=20, timeout_unit="us")
async def test_vps_05_reset_priority(dut) -> None:
    """VPS-05: rst_n 0 with en 1 gives 0."""
    env = CntEnv(dut, "test_vps_05_reset_priority")
    await env.start()
    # skeleton: count nonzero with en 1, then rst_n 0 with en 1 for 3 edges (waits for the RTL)
    env.finish("VPS-05", 3)


@cocotb.test(timeout_time=20, timeout_unit="us")
async def test_vps_06_coverage_all_values(dut) -> None:
    """VPS-06: 17 enabled edges from reset visit 0 to 15 and wrap."""
    env = CntEnv(dut, "test_vps_06_coverage_all_values")
    await env.start()
    # skeleton: 17 enabled edges (waits for the RTL)
    env.finish("VPS-06", 17)


@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_random_seeded(dut) -> None:
    """Constrained-random en and rst_n from the testplan's constraint model, one seed."""
    env = CntEnv(dut, "test_random_seeded")
    await env.start()
    for _ in range(RANDOM_EDGES):
        if env.rng.random() < RESET_PROB:
            await env.reset.assert_reset()
            await env.reset.release(env.rng.randint(1, RESET_MAX_EDGES))
        await env.driver.drive(int(env.rng.random() < EN_PROB))
    env.finish("VPS-06", 1)


# ==== D. Reference model and scoreboard ===========================================
class CntModel:
    """REQ-3.1.1 to REQ-3.1.6 at the ports; never reads inside the DUT."""

    def __init__(self) -> None:
        self.count_exp = 0

    def apply(self, rst_n: int, en: int) -> int:
        if not rst_n:
            self.count_exp = 0  # REQ-3.1.1, REQ-3.1.6
        elif en:
            self.count_exp = (self.count_exp + 1) & CNT_MAX  # REQ-3.1.2, REQ-3.1.3
        return self.count_exp  # REQ-3.1.4: hold


@dataclass(frozen=True)
class CntMatch:
    vps: str
    count_before: int
    sample: CntSample


def cnt_class(value: int) -> str:
    return "zero" if value == 0 else "max" if value == CNT_MAX else "mid"


class CntScoreboard:
    """Compares every edge with the model: one MISMATCH line per difference."""

    def __init__(self, test: str, seed: int) -> None:
        self.test = test
        self.seed = seed
        self.model = CntModel()
        self.count_before = 0
        self.started = False
        self.checked: dict[str, int] = {}
        self.listeners: list[Callable[[CntMatch], None]] = []

    def observe(self, sample: CntSample) -> None:
        """Skeleton: compare sample.count with the model, count and sample the scenario."""
        expected = self.model.apply(sample.rst_n, sample.en)
        if sample.rst_n:
            self.started = True
        if sample.count != expected and (self.started or not sample.rst_n):
            raise AssertionError(
                f"MISMATCH VPS-01 REQ-3.1.1 signal=count expected={expected} "
                f"observed={sample.count} test={self.test} seed={self.seed}"
            )
        self.count_before = sample.count


# ==== E. Coverage model ===========================================================
@CoverPoint(
    "cg_vps_01.count_at",
    xf=lambda m: cnt_class(m.count_before),
    bins=["zero", "mid", "max"],
)
def cg_vps_01(m: CntMatch) -> None:
    """VPS-01: count when the reset came."""


@CoverPoint("cg_vps_02.en_state", xf=lambda m: "low_after_count", bins=["low_after_count"])
def cg_vps_02(m: CntMatch) -> None:
    """VPS-02: en low after a count."""


@CoverPoint(
    "cg_vps_03.count_at",
    xf=lambda m: "zero" if m.count_before == 0 else "mid",
    bins=["zero", "mid"],
)
def cg_vps_03(m: CntMatch) -> None:
    """VPS-03: count before an increment."""


@CoverPoint("cg_vps_04.count_at", xf=lambda m: "max", bins=["max"])
def cg_vps_04(m: CntMatch) -> None:
    """VPS-04: wrap from 15."""


@CoverPoint("cg_vps_05.en_state", xf=lambda m: "high_in_reset", bins=["high_in_reset"])
def cg_vps_05(m: CntMatch) -> None:
    """VPS-05: en high while in reset."""


@CoverPoint(
    "cg_vps_06.count_at",
    xf=lambda m: cnt_class(m.count_before),
    bins=["zero", "mid", "max"],
)
def cg_vps_06(m: CntMatch) -> None:
    """VPS-06: count values visited."""


CNT_COVERGROUPS: dict[str, Callable[[CntMatch], None]] = {
    "VPS-01": cg_vps_01,
    "VPS-02": cg_vps_02,
    "VPS-03": cg_vps_03,
    "VPS-04": cg_vps_04,
    "VPS-05": cg_vps_05,
    "VPS-06": cg_vps_06,
}


def cnt_cov_sample(match: CntMatch) -> None:
    CNT_COVERGROUPS[match.vps](match)


# ==== F. Properties ===============================================================
# None: the risk map requires no formal property for counter4d.

# ==== G. Regression manifest ======================================================
# verif/seeds.yaml is kept by cocotb_sim.
