from __future__ import annotations

from dataclasses import dataclass

from pint import UnitRegistry


ureg = UnitRegistry()

ureg.formatter.default_format = "C"

_Q = ureg.Quantity  # type: ignore[assignment]


def _require_quantity(name: str, value: _Q, dimensionality: str) -> None:
    if not isinstance(value, _Q):
        raise TypeError(
            f"{name} must be a quantity created with design_rules.ureg, got {type(value).__name__}"
        )
    if not value.check(dimensionality):
        raise ValueError(f"{name} must have dimensionality {dimensionality}, got {value.units}")


@dataclass(frozen=True)
class DesignConstants:
    """Process capacitance densities."""

    c_jpa: _Q  # p+ area cap density [aF/um^2]
    c_jpp: _Q  # p+ perimeter cap density [aF/um]
    c_jna: _Q  # n+ area cap density [aF/um^2]
    c_jnp: _Q  # n+ perimeter cap density [aF/um]
    c_ox: _Q   # gate cap density [aF/um^2]

    def __post_init__(self) -> None:
        _require_quantity("c_jpa", self.c_jpa, "[capacitance] / [length] ** 2")
        _require_quantity("c_jpp", self.c_jpp, "[capacitance] / [length]")
        _require_quantity("c_jna", self.c_jna, "[capacitance] / [length] ** 2")
        _require_quantity("c_jnp", self.c_jnp, "[capacitance] / [length]")
        _require_quantity("c_ox", self.c_ox, "[capacitance] / [length] ** 2")


@dataclass(frozen=True)
class Geometry:
    """Geometry and common diffusion segment lengths [um]."""

    w: _Q
    l: _Q
    diff_con: _Q  # Contacted diffusion segment length
    diff_end: _Q  # End diffusion segment length
    diff_unc: _Q  # Uncontacted diffusion segment length

    def __post_init__(self) -> None:
        _require_quantity("w", self.w, "[length]")
        _require_quantity("l", self.l, "[length]")
        _require_quantity("diff_con", self.diff_con, "[length]")
        _require_quantity("diff_end", self.diff_end, "[length]")
        _require_quantity("diff_unc", self.diff_unc, "[length]")


@dataclass(frozen=True)
class CapacitanceTerms:
    """Precomputed capacitance terms [aF] for common segment types."""

    c_p_con: _Q
    c_p_end: _Q
    c_p_unc: _Q
    c_n_con: _Q
    c_n_end: _Q
    c_n_unc: _Q
    c_gate: _Q


DEFAULT_GEOMETRY = Geometry(
    w=0.20 * ureg.um,
    l=0.10 * ureg.um,
    diff_con=0.26 * ureg.um,
    diff_end=0.23 * ureg.um,
    diff_unc=0.15 * ureg.um,
)


@dataclass
class CapacitanceModel:
    constants: DesignConstants
    geometry: Geometry = DEFAULT_GEOMETRY

    @staticmethod
    def _junction_cap(
        w: _Q,
        l: _Q,
        area_density: _Q,
        perim_density: _Q,
    ) -> _Q:
        _require_quantity("w", w, "[length]")
        _require_quantity("l", l, "[length]")
        _require_quantity("area_density", area_density, "[capacitance] / [length] ** 2")
        _require_quantity("perim_density", perim_density, "[capacitance] / [length]")
        area = w * l
        perimeter = 2 * (w + l)
        return area_density * area + perim_density * perimeter

    def c_p(self, w: _Q, l: _Q) -> _Q:
        c = self.constants
        return self._junction_cap(w, l, c.c_jpa, c.c_jpp)

    def c_n(self, w: _Q, l: _Q) -> _Q:
        c = self.constants
        return self._junction_cap(w, l, c.c_jna, c.c_jnp)

    def c_g(self, w: _Q, l: _Q) -> _Q:
        _require_quantity("w", w, "[length]")
        _require_quantity("l", l, "[length]")
        return self.constants.c_ox * w * l

    def _explain_junction(
        self,
        label: str,
        w: _Q,
        l: _Q,
        area_density: _Q,
        perim_density: _Q,
        area_name: str,
        perim_name: str,
    ) -> list[str]:
        area = w * l
        perimeter = 2.0 * (w + l)
        area_term = area_density * area
        perim_term = perim_density * perimeter
        total = area_term + perim_term
        return [
            f"{label} = {area_name}*A + {perim_name}*P",
            f"A = w*l = {w:.3f}*{l:.3f} = {area:.5f} um^2",
            f"P = 2*(w + l) = 2*({w:.3f} + {l:.3f}) = {perimeter:.5f} um",
            f"{label} = {area_density:.3f}*{area:.5f} + {perim_density:.3f}*{perimeter:.5f}",
            f"{label} = {area_term:.5f} + {perim_term:.5f} = {total:.5f} aF",
        ]

    def explain_c_p(self, w: _Q, l: _Q) -> list[str]:
        c = self.constants
        return self._explain_junction("C_p", w, l, c.c_jpa, c.c_jpp, "C_jpa", "C_jpp")

    def explain_c_n(self, w: _Q, l: _Q) -> list[str]:
        c = self.constants
        return self._explain_junction("C_n", w, l, c.c_jna, c.c_jnp, "C_jna", "C_jnp")

    def explain_c_g(self, w: _Q, l: _Q) -> list[str]:
        c_ox = self.constants.c_ox
        cap = self.c_g(w, l)
        return [
            "C_g = C_ox*w*l",
            f"C_g = {c_ox:.3f}*{w:.3f}*{l:.3f}",
            f"C_g = {cap:.5f} aF",
        ]

    def explain_term(self, term_name: str) -> list[str]:
        """Explain one named term using this model's constants and geometry."""
        g = self.geometry
        key = term_name.lower()
        term_map = {
            "c_p_con": lambda: self.explain_c_p(g.w, g.diff_con),
            "c_p_end": lambda: self.explain_c_p(g.w, g.diff_end),
            "c_p_unc": lambda: self.explain_c_p(g.w, g.diff_unc),
            "c_n_con": lambda: self.explain_c_n(g.w, g.diff_con),
            "c_n_end": lambda: self.explain_c_n(g.w, g.diff_end),
            "c_n_unc": lambda: self.explain_c_n(g.w, g.diff_unc),
            "c_gate": lambda: self.explain_c_g(g.w, g.l),
        }
        if key not in term_map:
            valid = ", ".join(sorted(term_map))
            raise KeyError(f"Unknown term '{term_name}'. Valid terms: {valid}")
        return term_map[key]()

    def capacitance_terms(self) -> CapacitanceTerms:
        """Convenience bundle so formulas can be composed outside this module."""
        geometry = self.geometry
        return CapacitanceTerms(
            c_p_con=self.c_p(geometry.w, geometry.diff_con),
            c_p_end=self.c_p(geometry.w, geometry.diff_end),
            c_p_unc=self.c_p(geometry.w, geometry.diff_unc),
            c_n_con=self.c_n(geometry.w, geometry.diff_con),
            c_n_end=self.c_n(geometry.w, geometry.diff_end),
            c_n_unc=self.c_n(geometry.w, geometry.diff_unc),
            c_gate=self.c_g(geometry.w, geometry.l),
        )


# From your notebook:
DEFAULT_90NM = DesignConstants(
    c_jpa=1462.0 * ureg.aF / ureg.um**2,
    c_jpp=30.0 * ureg.aF / ureg.um,
    c_jna=1392.0 * ureg.aF / ureg.um**2,
    c_jnp=20.0 * ureg.aF / ureg.um,
    c_ox=21570.0 * ureg.aF / ureg.um**2,
)

F16_EXAM = DesignConstants(
    c_jpa=1462.0 * ureg.aF / ureg.um**2,
    c_jpp=30.0 * ureg.aF / ureg.um,
    c_jna=1601.0 * ureg.aF / ureg.um**2,
    c_jnp=23.0 * ureg.aF / ureg.um,
    c_ox=22500.0 * ureg.aF / ureg.um**2,
)
