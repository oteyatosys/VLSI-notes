from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignConstants:
    """Process capacitance densities."""

    c_jpa: float  # p+ area cap density [aF/um^2]
    c_jpp: float  # p+ perimeter cap density [aF/um]
    c_jna: float  # n+ area cap density [aF/um^2]
    c_jnp: float  # n+ perimeter cap density [aF/um]
    c_ox: float   # gate cap density [aF/um^2]


@dataclass(frozen=True)
class Geometry:
    """Geometry and common diffusion segment lengths [um]."""

    w: float
    l: float
    diff_con: float
    diff_end: float
    diff_unc: float


@dataclass(frozen=True)
class CapacitanceTerms:
    """Precomputed capacitance terms [aF] for common segment types."""

    c_p_con: float
    c_p_end: float
    c_p_unc: float
    c_n_con: float
    c_n_end: float
    c_n_unc: float
    c_gate: float


DEFAULT_GEOMETRY = Geometry(
    w=0.20,
    l=0.10,
    diff_con=0.26,
    diff_end=0.23,
    diff_unc=0.15,
)


@dataclass
class CapacitanceModel:
    constants: DesignConstants
    geometry: Geometry = DEFAULT_GEOMETRY

    @staticmethod
    def _junction_cap(w: float, l: float, area_density: float, perim_density: float) -> float:
        area = w * l
        perimeter = 2.0 * (w + l)
        return area_density * area + perim_density * perimeter

    def c_p(self, w: float, l: float) -> float:
        c = self.constants
        return self._junction_cap(w, l, c.c_jpa, c.c_jpp)

    def c_n(self, w: float, l: float) -> float:
        c = self.constants
        return self._junction_cap(w, l, c.c_jna, c.c_jnp)

    def c_g(self, w: float, l: float) -> float:
        return self.constants.c_ox * w * l

    def _explain_junction(
        self,
        label: str,
        w: float,
        l: float,
        area_density: float,
        perim_density: float,
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

    def explain_c_p(self, w: float, l: float) -> list[str]:
        c = self.constants
        return self._explain_junction("C_p", w, l, c.c_jpa, c.c_jpp, "C_jpa", "C_jpp")

    def explain_c_n(self, w: float, l: float) -> list[str]:
        c = self.constants
        return self._explain_junction("C_n", w, l, c.c_jna, c.c_jnp, "C_jna", "C_jnp")

    def explain_c_g(self, w: float, l: float) -> list[str]:
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
    c_jpa=1462.0,
    c_jpp=30.0,
    c_jna=1392.0,
    c_jnp=20.0,
    c_ox=21570.0,
)

F16_EXAM = DesignConstants(
    c_jpa=1462.0,
    c_jpp=30.0,
    c_jna=1601.0,
    c_jnp=23.0,
    c_ox=22500.0,
)
