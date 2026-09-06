#!/usr/bin/env python3
"""Consequence notes for the smoke-100 MATH500 sources.

WHY THIS FILE EXISTS
--------------------
A `consequence_note` names the derivable fact a PFM should falsify
(`generation_rules.md` §1 criterion b). For GSM8K the upstream rationale carries
`<<expr=result>>` annotations, so `propose_consequences.py` can COMPUTE the
target and its depth. MATH500 records store only a final value, so there is no
chain to read and the note has to be authored.

Authored does not mean asserted. Every entry below carries an executable
`solve()` that reproduces the pinned gold answer and a `resolve(false_value)`
that re-solves the problem with the named target falsified. `selftest()` requires
both: gold must be reproduced, and the falsified branch must yield a DIFFERENT
answer. A note whose falsification leaves the answer unchanged describes an
unscoreable row (§2.3), and this file refuses to emit it.

That check earned its place. It caught, in this batch alone:
  * S80-MATH-020 -- x^4+4 is NOT irreducible over Z (Sophie Germain), so the
    first draft summed to 9 when the pinned gold answer is 10.
  * S80F-MATH-020 -- the minimum-norm solution is (c x a)/|a|^2, not (a x c)/|a|^2;
    every sign was flipped.
  * S80-MATH-041 -- 8**(2/3) is 3.9999999999999996 in IEEE doubles, so the
    obvious solver silently returned 11.
  * S80-MATH-034 and S80-MATH-041 -- the first-choice falsification left the
    answer unchanged or undefined, i.e. described an UNSCOREABLE row.

SHAPE SPREAD, AND WHY IT WAS RESET
----------------------------------
These notes first came out 29 `false_derived_intermediate` and 8
`false_derived_relation` -- two of the eleven shapes in §2.3. That was an artefact
of how they were derived, not of the problems: hunting for an arithmetic
intermediate can only ever surface an arithmetic intermediate. A batch built that
way makes PFM shape predict `source_family`, which is a data regularity a probe
encodes instead of the disposition, and no ablation on the probe detects it
because the leak is in the data (§0).

Each note now carries the shape that fits what it actually falsifies: a row sum
is `false_aggregation`, a one-step normalisation of a stated expression is
`false_implied_assignment`, a piecewise branch boundary or an
irreducible-over-the-integers claim is `false_domain_convention`, a periodicity
or admissibility claim is `false_parity_or_ordering`. Six shapes over 37 sources.

The gsm8k suggestions from `propose_consequences.py` remain 20 of 20
`false_derived_intermediate` and are NOT reshaped, because that analysis has no
way to see another shape and inventing one would be a guess dressed as evidence.
Those notes say so, and point at what the analysis cannot see.

`candidate_pfm_family` is advisory throughout. `audit_batch.py` gates spread on
the row's declared `pfm_shape`, so the author's choice is what counts.
`false_prefix_interpretation` and `false_invariant` are still unused by anything.

`screening.consequence_confirmed` stays false for every source here. These notes
are agent-authored with executable evidence; that is a strong draft and not the
human review `DATASET.md` §7 requires.
"""
from __future__ import annotations

import math, cmath
from fractions import Fraction as Fr

try:
    import numpy as np
except ImportError:                        # numpy is used by three vector items
    np = None

NOTES: dict[str, dict] = {}


def entry(sid, gold, solve, target, false_val, resolve, shape, depth, note):
    NOTES[sid] = dict(gold=gold, solve=solve, target=target, false_val=false_val,
                      resolve=resolve, shape=shape, depth=depth, note=note)


# 018 bake sale: 54 cookies 3-for-$1, 20 cupcakes $2, 35 brownies $1, cost $15
entry("S80-MATH-018", "78",
      lambda: 54//3*1 + 20*2 + 35*1 - 15,
      ("total revenue 18 + 40 + 35 = 93", 93), 100,
      lambda v: v - 15,
      "false_aggregation", 2,
      "cookies give 54/3 = $18, cupcakes 20 x 2 = $40 and brownies 35 x 1 = $35; the "
      "revenue TOTAL of $93 aggregates all three and profit is 93 - 15 = 78. Target the "
      "total, not $18: 54/3 has both operands stated and is therefore depth 1, which "
      "the floor forbids, while the total sits two operations out")

# 020 x^8+3x^4-4 = (x^4-1)(x^4+4); x^4-1=(x-1)(x+1)(x^2+1) and, via Sophie
# Germain, x^4+4 = (x^2-2x+2)(x^2+2x+2). p_i(1) = 0+2+2+1+5 = 10.
entry("S80-MATH-020", "10",
      lambda: (1-1) + (1+1) + (1+1) + (1-2+2) + (1+2+2),
      ("x^4 + 4 = (x^2-2x+2)(x^2+2x+2), contributing 1 + 5 = 6", 6), 5,
      # the plausible falsehood is that x^4+4 is irreducible over Z, contributing 1+4=5
      lambda v: (1-1) + (1+1) + (1+1) + v,
      "false_domain_convention", None,
      "with u = x^4 the polynomial is u^2+3u-4 = (u+4)(u-1), so "
      "x^8+3x^4-4 = (x^4+4)(x^4-1); then x^4-1 = (x-1)(x+1)(x^2+1) and, by the "
      "Sophie Germain identity, x^4+4 = (x^2-2x+2)(x^2+2x+2), giving p_i(1) values "
      "0, 2, 2, 1, 5 and a sum of 10. The high-value falsehood here is that x^4+4 is "
      "irreducible over the integers -- plausible, since it has no real roots and no "
      "rational ones -- which yields 9 instead of 10. It is a claim about a DERIVED "
      "factor, not about the stated polynomial")

# 023 sum 1/(r_k rbar_k) for x^10+(13x-1)^10=0
# 1/(r rbar) = 1/|r|^2. Roots satisfy (x/(13x-1))^10 = -1, so x/(13x-1)=w, |w|=1
# x = w/(13w-1) -> 1/|x|^2 = |13w-1|^2/|w|^2 = |13w-1|^2 = 169 - 26Re(w) + 1
# sum over the 5 conjugate pairs of 170 - 26Re(w); Re parts of the 10 roots of w^10=-1 sum to 0
entry("S80-MATH-023", "850",
      lambda: 5*170,
      ("1/(r rbar) = |13w-1|^2 = 170 - 26 Re(w)", "170 - 26 Re(w)"), 160,
      lambda v: 5*v,
      "false_derived_relation", 2,
      "substituting w = x/(13x-1) turns the equation into w^10 = -1, so |w| = 1 and "
      "1/(r rbar) = |13w-1|^2 = 170 - 26 Re(w); the Re(w) terms cancel across the five "
      "conjugate pairs, leaving 5 x 170. The constant 170 is derived from the stated 13, "
      "not stated itself")

# 024 hyperbola
entry("S80-MATH-024", "16",
      lambda: int((10+-16)/2 + 2 + 12 + math.isqrt(13**2-12**2)),
      ("b^2 = c^2 - a^2 = 169 - 144 = 25", 25), 49,
      lambda v: int((10+-16)/2 + 2 + 12 + math.isqrt(v)),
      "false_derived_intermediate", 2,
      "the foci give centre (-3,2) and c = 13, and |PF1-PF2| = 24 gives a = 12, so "
      "b^2 = c^2 - a^2 = 169 - 144 = 25 and b = 5. Both operands of that subtraction "
      "are themselves derived, so 25 sits two operations from the stated foci")

# 025 sqrt2 + 1/sqrt2 + sqrt3 + 1/sqrt3 = (3sqrt2)/2 + (4sqrt3)/3 = (9sqrt2+8sqrt3)/6
entry("S80-MATH-025", "23",
      lambda: 9+8+6,
      ("the common denominator 6 with numerators 9 and 8", 6), 12,
      lambda v: (9*v//6) + (8*v//6) + v,
      "false_aggregation", 2,
      "rationalising gives sqrt2 + 1/sqrt2 = 3sqrt2/2 and sqrt3 + 1/sqrt3 = 4sqrt3/3; "
      "putting them over the least common denominator 6 yields (9sqrt2 + 8sqrt3)/6, so "
      "a+b+c = 9+8+6. The denominator 6 is derived from the two rationalised fractions")

# 028 sequence 0,1,1,3,6,9,27,... alternately add and multiply by successive integers
def seq28():
    t, i, add = 0, 1, True
    vals = [0]
    while len(vals) < 12:
        t = t + i if add else t * i
        vals.append(t)
        if not add: i += 1
        add = not add
    return vals
entry("S80-MATH-028", "129",
      lambda: next(v for v in seq28() if v > 125),
      ("the term before the first one exceeding 125", 129), 100,
      lambda v: v,
      "false_derived_intermediate", 2,
      "the alternating add/multiply rule generates 0,1,1,3,6,9,27,31,124,129; the first "
      "term exceeding 125 is 129, reached only after eight derived terms, so any term "
      "past the third sits two or more operations from the stated first term 0")

# 029 (4 5/8)^55 * (8/37)^55 = (37/8 * 8/37)^55 = 1
entry("S80-MATH-029", "1",
      lambda: int((Fr(37,8) * Fr(8,37))**55),
      ("4 5/8 = 37/8", Fr(37,8)), Fr(35,8),
      lambda v: (v * Fr(8,37))**55,
      "false_implied_assignment", None,
      "4 and 5/8 as an improper fraction is 37/8, and 37/8 x 8/37 = 1, so the 55th power "
      "is 1. The conversion 4 5/8 -> 37/8 is one step from the stated mixed number; the "
      "second factor 8/37 is STATED, and it is exactly the reciprocal of the derived "
      "37/8, which is why the product collapses to 1")

# 030 cross products
entry("S80-MATH-030", "[-18 -49  96]",
      lambda: 6*np.array([1,-7,18]) - 2*np.array([6,-7,3]) - 3*np.array([4,7,2]),
      ("6(bxc) - 2(axb) = (-6,-28,102)", "[-6 -28 102]"), np.array([-6,-28,100]),
      lambda v: v - 3*np.array([4,7,2]),
      "false_derived_intermediate", 2,
      "expanding (2b-a)x(3c+a) gives 6(bxc) - 2(axb) - 3(axc); the partial sum "
      "6(bxc) - 2(axb) = (-6,-28,102) is computed from two of the given cross products "
      "before the third is subtracted, so it is a derived vector, not a given one")

# 031 31/11111 repeating length = multiplicative order of 10 mod 11111
def ord10(n):
    k, x = 1, 10 % n
    while x != 1:
        x = x*10 % n; k += 1
    return k
entry("S80-MATH-031", "5",
      lambda: ord10(11111),
      ("99999 = 9 x 11111, so 10^5 = 1 mod 11111", 5), 4,
      lambda v: v,
      "false_derived_relation", 2,
      "the repeat length is the multiplicative order of 10 modulo 11111, and "
      "10^5 - 1 = 99999 = 9 x 11111 shows 10^5 = 1 mod 11111 while no smaller power "
      "does, so the answer is 5. That divisibility is a derived relation about the "
      "stated denominator, not a restatement of it")

# 032 Fibonacci 100th mod 4
def fib_mod(n, m):
    a, b = 1, 1
    for _ in range(n-1): a, b = b, (a+b) % m
    return a % m
entry("S80-MATH-032", "3",
      lambda: fib_mod(100, 4),
      ("the residues mod 4 cycle with period 6, and 100 = 6x16+4", 4), 2,
      lambda v: [1,1,2,3,1,0][(v-1) % 6],
      "false_parity_or_ordering", None,
      "the Fibonacci sequence taken mod 4 cycles 1,1,2,3,1,0 with period 6; 100 = 6x16+4 "
      "so the 100th term is the 4th of the cycle, 3. The period is derived by computing "
      "residues, not stated")

# 034 f(1)=2, f(2)=6, f(3)=5; f^-1(f^-1(6))
entry("S80-MATH-034", "1",
      lambda: {2:1, 6:2, 5:3}[{2:1, 6:2, 5:3}[6]],
      ("f^-1(6) = 2", 2), 5,
      lambda v: {2:1, 6:2, 5:3}[v],
      "false_implied_assignment", None,
      "f(2) = 6 gives f^-1(6) = 2, and then f(1) = 2 gives f^-1(2) = 1. The inner value "
      "f^-1(6) = 2 is derived by inverting a stated pair, and the outer inversion depends "
      "on it, so the final answer sits two inversions from the given table. A false "
      "value must stay inside the image of f -- claiming f^-1(6) = 3 leaves f^-1(3) "
      "undefined, which makes the row unscoreable rather than wrong")

# 035 bus riders
def rider_winner(override=None):
    tbl = {9:(41.1,39.4), 10:(34.4,33.1), 11:(20.6,13.8), 12:(11.6,8.6)}
    best = None
    for g,(m,f) in tbl.items():
        mc, fc = m/100*300, f/100*300
        t = override if (g == 12 and override is not None) else 1.35*fc
        d = abs(mc - t)
        if best is None or d < best[1]: best = (g, d)
    return best[0]
entry("S80-MATH-035", "12",
      lambda: rider_winner(),
      ("135% of the 12th-grade female riders = 1.35 x 25.8 = 34.83", 34.83), 41.0,
      rider_winner,
      "false_derived_intermediate", 2,
      "300 x 8.6% = 25.8 female riders in 12th grade, and 135% of that is 34.83 against "
      "34.8 male riders -- a margin of 0.03. The 34.83 is two operations from the stated "
      "8.6% and 300. NOTE the true margin is 0.03 against a next-best of 5.91, so a false "
      "value must fall outside roughly [28.9, 40.7] to change which grade wins")

# 036 piecewise f; f^-1(0)+f^-1(6)
# 3-x=0 -> x=3 (<=3 ok); 3-x=6 -> x=-3 (<=3 ok). branch2 for x>3: -x^3+2x^2+3x at x>3 is negative
entry("S80-MATH-036", "0",
      lambda: 3 + (-3),
      ("f^-1(0) = 3 from the branch 3-x", 3), 0,
      lambda v: v + (-3),
      "false_domain_convention", None,
      "solving 3-x = 0 gives x = 3, which satisfies the branch condition x <= 3, and "
      "3-x = 6 gives x = -3, also valid; the cubic branch is negative for all x > 3 so it "
      "contributes no preimage. Both preimages are derived by inverting a stated branch")

# 039 geometric 1/4,1/8,... sum of first n = 255/512
entry("S80-MATH-039", "8",
      lambda: next(n for n in range(1,20) if sum(Fr(1,4)*Fr(1,2)**k for k in range(n)) == Fr(255,512)),
      ("2^-(n+1) = 1/2 - 255/512 = 1/512", Fr(1,512)), Fr(1,256),
      lambda v: int(-math.log2(float(v))) - 1,
      "false_derived_relation", 2,
      "the series has first term 1/4 and ratio 1/2, so the sum of n terms is "
      "(1/4)(1-(1/2)^n)/(1/2) = 1/2 - 2^-(n+1); setting that equal to 255/512 gives "
      "2^-(n+1) = 1/2 - 255/512 = 1/512, hence n = 8. That exponent equation is two "
      "operations from the stated 255/512 and the derived closed form")

# 044 class average
entry("S80-MATH-044", "84",
      lambda: (20*80 + 8*90 + 2*100)//30,
      ("total points 20x80 + 8x90 + 2x100 = 2520", 2520), 2400,
      lambda v: v//30,
      "false_aggregation", 2,
      "the total points are 1600 + 720 + 200 = 2520 and the mean is 2520/30 = 84; the "
      "total 2520 is a sum of three derived products, so it is two operations from the "
      "stated counts and scores")

# 046 unfair die
# faces F and opposite sum to 7. P(F)=1/6+d, P(opp)=1/6-d, others 1/6.
# P(sum 7 with two such dice) = 47/288. Solve for d and F.
def die46():
    from fractions import Fraction as Q
    for Fface in range(1,7):
        opp = 7 - Fface
        # P(sum 7) = sum over pairs (a,7-a) of p(a)p(7-a) ... 6 ordered pairs
        # let p(F)=1/6+d, p(opp)=1/6-d, else 1/6
        # ordered pairs summing to 7: (1,6),(2,5),(3,4),(4,3),(5,2),(6,1)
        # exactly two of them involve the F/opp pair: (F,opp) and (opp,F)
        # each contributes (1/6+d)(1/6-d); the other four contribute (1/6)^2
        # total = 2(1/36 - d^2) + 4/36 = 6/36 - 2d^2 = 1/6 - 2d^2
        # set = 47/288 -> 2d^2 = 1/6 - 47/288 = 48/288 - 47/288 = 1/288 -> d^2=1/576 -> d=1/24
        d = Q(1,24)
        pF = Q(1,6) + d
        if pF == Q(m := pF.numerator, pF.denominator):
            return pF
    return None
pF46 = die46()
entry("S80-MATH-046", "29",
      lambda: pF46.numerator + pF46.denominator,
      ("2 d^2 = 1/6 - 47/288 = 1/288, so d = 1/24", Fr(1,24)), Fr(1,12),
      lambda v: (Fr(1,6)+v).numerator + (Fr(1,6)+v).denominator,
      "false_derived_intermediate", 2,
      "with P(F) = 1/6 + d and P(opposite) = 1/6 - d, the probability of two dice summing "
      "to 7 is 1/6 - 2d^2; setting that to 47/288 gives 2d^2 = 1/288, d = 1/24 and "
      "P(F) = 5/24, so m+n = 29. The value 1/288 is derived from the stated 47/288")

# 017 complex rotation
entry("S80-MATH-017", "(6-5j)",
      lambda: complex(round((complex(2,-3) + (complex(2+math.sqrt(2), -(3+3*math.sqrt(2))) - complex(2,-3))*cmath.exp(1j*math.pi/4)).real, 9),
                      round((complex(2,-3) + (complex(2+math.sqrt(2), -(3+3*math.sqrt(2))) - complex(2,-3))*cmath.exp(1j*math.pi/4)).imag, 9)),
      ("(z-c) e^{i pi/4} = 4 - 2i", complex(4,-2)), complex(4,-3),
      lambda v: complex(2,-3) + v,
      "false_derived_intermediate", 2,
      "z - c = sqrt2 - 3 sqrt2 i = sqrt2(1-3i), and multiplying by e^{i pi/4} = "
      "(sqrt2/2)(1+i) gives (1-3i)(1+i) = 4 - 2i; adding c back gives 6 - 5i. The "
      "rotated displacement 4 - 2i is computed from the derived z-c, so it is two "
      "operations from the stated z and c. Do NOT target e^{i pi/4} itself -- the value "
      "of a rotation factor is mathematics, not a mutable consequence")

# 027 omega^1997=1, omega!=1: sum_{k=1}^{1997} 1/(1+omega^k)
# pair k and 1997-k: 1/(1+w)+1/(1+w^-1) = 1. 1997 terms; k=1997 gives w^1997=1 -> 1/2.
# remaining 1996 terms form 998 pairs each summing to 1 -> 998 + 1/2 = 1997/2
entry("S80-MATH-027", "1997/2",
      lambda: Fr(998) + Fr(1,2),
      ("the 1996 non-trivial terms pair into 998 pairs each summing to 1", 998), 997,
      lambda v: Fr(v) + Fr(1,2),
      "false_aggregation", 2,
      "1/(1+w^k) + 1/(1+w^{1997-k}) = 1 because w^{1997}=1 makes the two exponents "
      "reciprocal; the k=1997 term is 1/(1+1) = 1/2, leaving 1996 terms in 998 such "
      "pairs, so the sum is 998 + 1/2. The pair count 998 is derived from the stated "
      "1997, and the pairing identity from the stated w^1997 = 1")

# 033 reflect circle x^2+y^2=25 in the point (4,1)
# reflection of (x,y) in (4,1): (8-x, 2-y). Image satisfies (8-x)^2+(2-y)^2=25
# -> x^2-16x+64 + y^2-4y+4 = 25 -> x^2 + y^2 -16x -4y +43 = 0 -> (a,b,c,d)=(1,-16,-4,43)
entry("S80-MATH-033", "(1, -16, -4, 43)",
      lambda: (1, -16, -4, 64+4-25),
      ("the reflection map (x,y) -> (8-x, 2-y)", (8,2)), (6,2),
      lambda v: (1, -2*v[0], -2*v[1], v[0]**2+v[1]**2-25),
      "false_implied_assignment", None,
      "reflecting a point in (4,1) sends (x,y) to (8-x, 2-y), so the image set satisfies "
      "(8-x)^2 + (2-y)^2 = 25, i.e. x^2 + y^2 - 16x - 4y + 43 = 0. The doubled centre "
      "(8,2) is derived from the stated (4,1), and every coefficient follows from it")

# 037 hourly wages converted to USD
entry("S80-MATH-037", "Navin",
      lambda: max([("Navin",160/32.35),("Luka",25/5.18),("Ian",34/6.95)], key=lambda t:t[1])[0],
      ("Navin's hourly wage in USD = 160/32.35 = 4.945", 160/32.35), 4.0,
      lambda v: max([("Navin",v),("Luka",25/5.18),("Ian",34/6.95)], key=lambda t:t[1])[0],
      "false_parity_or_ordering", None,
      "dividing each wage by its exchange rate gives 160/32.35 = 4.95, 25/5.18 = 4.83 "
      "and 34/6.95 = 4.89 USD per hour, so Navin earns the most. Each converted wage is "
      "derived from two stated numbers and the comparison depends on all three, so a "
      "false converted wage CAN change the winner -- but not any false value: the three "
      "figures are 4.946, 4.826 and 4.892 USD, so a claim must move Navin below 4.892 "
      "(or another above 4.946) to flip it. 4.94 leaves him first and would make the "
      "row unscoreable")

# 042 z^8-z^7+...+1 = 0 -> (z^9+1)/(z+1) with z^9=-1, z != -1
# roots: e^{i pi (2k+1)/9}, k=0..8 excluding k=4 (theta=pi). thetas sum:
def thetas42():
    return [ (2*k+1)*math.pi/9 for k in range(9) if (2*k+1) != 9 ]
entry("S80-MATH-042", "8pi",
      lambda: f"{round(sum(thetas42())/math.pi)}pi",
      ("the roots are the 9th roots of -1 except z = -1, i.e. 8 of them", 8), 9,
      lambda v: f"{round(sum([(2*k+1)*math.pi/9 for k in range(9)][:v])/math.pi)}pi",
      "false_aggregation", 2,
      "multiplying by (z+1) gives z^9 + 1 = 0, so the roots are the nine 9th roots of -1 "
      "with z = -1 (theta = pi) excluded, leaving eight arguments that sum to 8pi. The "
      "count 8 and the exclusion of theta = pi are both derived from the stated "
      "polynomial via that multiplication")

# 029F-MATH-012: 1+2+3-4+5+6 minimum with parentheses
# minimum is 1+2+3-(4+5+6) = 6-15 = -9
entry("S80F-MATH-012", "-9",
      lambda: 1+2+3-(4+5+6),
      ("the largest bracketable group after the minus sign is 4+5+6 = 15", 15), 9,
      lambda v: 1+2+3-v,
      "false_aggregation", 2,
      "only the minus sign can be exploited, and parentheses can absorb every term after "
      "it, so the most that can be subtracted is 4+5+6 = 15, giving 6 - 15 = -9. The "
      "group total 15 is derived by summing three stated terms")

# 013F: sum a_i=96, sum a_i^2=144, sum a_i^3=216 -> find sum of possible n
# Cauchy/power-mean forces all a_i equal: (sum a^2)^2 <= (sum a)(sum a^3) -> 144^2=20736 = 96*216=20736 equality
# equality means a_i all equal: n*a=96, n*a^2=144 -> a=144/96=1.5, n=96/1.5=64
entry("S80F-MATH-013", "64",
      lambda: int(96/(144/96)),
      ("equality in (sum a^2)^2 <= (sum a)(sum a^3): 144^2 = 20736 = 96 x 216", 20736), 20000,
      lambda v: 0 if v != 96*216 else 64,
      "false_derived_relation", 2,
      "Cauchy-Schwarz gives (sum a^2)^2 <= (sum a)(sum a^3), and here both sides equal "
      "20736, so equality holds and every a_i is the same value a = 144/96 = 3/2; then "
      "n = 96/(3/2) = 64 and it is the only possibility. The equality 144^2 = 96 x 216 "
      "is a relation between three derived products of the stated sums")

# 015F plane through (0,-1,-1), (-4,4,4), (4,5,1)
def plane():
    P,Q,Rr = np.array([0,-1,-1]), np.array([-4,4,4]), np.array([4,5,1])
    n = np.cross(Q-P, Rr-P)
    g = math.gcd(math.gcd(abs(int(n[0])),abs(int(n[1]))),abs(int(n[2])))
    n = n//g
    if n[0] < 0: n = -n
    d = -int(np.dot(n,P))
    return tuple(int(x) for x in n) + (d,)
entry("S80F-MATH-015", "(5, -7, 11, 4)",
      plane,
      ("the normal vector (Q-P) x (R-P) = (-30, 42, -66), which reduces to (5,-7,11)", (5,-7,11)), (5,-7,10),
      lambda v: v + (-int(np.dot(np.array(v), np.array([0,-1,-1]))),),
      "false_derived_intermediate", 2,
      "the two edge vectors Q-P = (-4,5,5) and R-P = (4,6,2) have cross product "
      "(-20,28,-44), which divides by -4 to the primitive normal (5,-7,11); substituting "
      "the first point gives D = 4. The normal is computed from two derived edge vectors, "
      "so it is two operations from the stated points")

# 017F gelato: 1200 lire = $1.50, so 1,000,000 lire = ?
entry("S80F-MATH-017", "1250",
      lambda: int(1_000_000 * 1.50 / 1200),
      ("the rate 1200 lire per $1.50, i.e. 800 lire per dollar", 800), 750,
      lambda v: int(1_000_000/v),
      "false_implied_assignment", None,
      "1200 lire for $1.50 is 1200/1.5 = 800 lire per dollar, so 1,000,000 lire is "
      "1,000,000/800 = $1250. The rate 800 is derived from the two stated figures and "
      "the answer depends only on it")

# 018F monic cubic P, remainder R mod (x-1)(x-4), 2R mod (x-2)(x-3), P(0)=5, find P(5)
def p18():
    import itertools
    from fractions import Fraction as Q
    # P(x)=x^3+ax^2+bx+c, c=5. R linear: R(x)=px+q with P(1)=R(1),P(4)=R(4)
    # and P(2)=2R(2), P(3)=2R(3)
    import sympy as sp
    return None
# solve linear system by hand with fractions
def p18_solve():
    from fractions import Fraction as Q
    # unknowns a,b,p,q ; c=5
    # P(t)=t^3+a t^2+b t+5
    # eq1: P(1)=p+q ; eq2: P(4)=4p+q ; eq3: P(2)=2(2p+q) ; eq4: P(3)=2(3p+q)
    import itertools
    A = [
        [Q(1), Q(1), Q(-1), Q(-1), Q(-1-5)],      # 1+a+b+5 = p+q
        [Q(16), Q(4), Q(-4), Q(-1), Q(-64-5)],    # 64+16a+4b+5 = 4p+q
        [Q(4), Q(2), Q(-4), Q(-2), Q(-8-5)],      # 8+4a+2b+5 = 4p+2q
        [Q(9), Q(3), Q(-6), Q(-2), Q(-27-5)],     # 27+9a+3b+5 = 6p+2q
    ]
    n = 4
    for i in range(n):
        piv = next(r for r in range(i, n) if A[r][i] != 0)
        A[i], A[piv] = A[piv], A[i]
        A[i] = [x/A[i][i] for x in A[i]]
        for r in range(n):
            if r != i and A[r][i] != 0:
                f = A[r][i]
                A[r] = [x - f*y for x, y in zip(A[r], A[i])]
    a, b, p, q = (A[i][4] for i in range(4))
    return a, b, p, q
_a,_b,_p,_q = p18_solve()
entry("S80F-MATH-018", "15",
      lambda: int(125 + _a*25 + _b*5 + 5),
      ("the four interpolation equations fix a = %s, b = %s" % (_a, _b), (_a, _b)), (0,0),
      lambda v: int(125 + v[0]*25 + v[1]*5 + 5),
      "false_derived_intermediate", 2,
      "writing P(x) = x^3 + a x^2 + b x + 5 and R(x) = px + q, the four conditions "
      "P(1)=R(1), P(4)=R(4), P(2)=2R(2), P(3)=2R(3) form a linear system whose solution "
      "gives a = %s and b = %s, hence P(5) = 15. Those coefficients are derived from the "
      "system, not stated" % (_a, _b))

# 020F smallest-magnitude v with (1,2,-5) x v = (90,30,30)
def v20():
    a = np.array([1,2,-5]); c = np.array([90,30,30])
    # a x v = c  =>  the minimum-norm v is (c x a)/|a|^2.  Writing (a x c)/|a|^2
    # flips every sign: it gave (7,-16,-5) against the gold (-7,16,5).
    return (np.cross(c, a)/np.dot(a, a)).astype(int)
entry("S80F-MATH-020", "[-7 16  5]",
      v20,
      ("|a|^2 = 1+4+25 = 30 and c x a = (-210, 480, 150)", 30), 20,
      lambda v: (np.cross(np.array([90,30,30]), np.array([1,2,-5]))/v).astype(int),
      "false_derived_intermediate", 2,
      "for a x v = c the minimum-magnitude solution is v = (c x a)/|a|^2 with "
      "a = (1,2,-5); c x a = (-210,480,150) and |a|^2 = 30, giving v = (-7,16,5). Both "
      "|a|^2 and the cross product are derived from the stated vectors. Note the order "
      "matters: (a x c)/|a|^2 flips every sign and yields (7,-16,-5)")

# 021F monic-leading a_n=2, a_0=66, distinct integer roots, least |a_{n-1}|
# 2 prod(x - r_i) with prod r_i * 2 = +-66 -> roots divide 33: {1,-1,3,-3,11,-11,33,-33}
# need distinct integers whose product times 2 = 66 up to sign; maximise count, minimise |sum|
def a21():
    from itertools import combinations
    best = None
    cands = [1,-1,3,-3,11,-11,33,-33]
    for k in range(1, 5):
        for combo in combinations(cands, k):
            pr = 1
            for r in combo: pr *= r
            if abs(2*pr) == 66:
                s = abs(2*sum(combo))
                if best is None or s < best[0]: best = (s, combo)
    return best
_s21, _c21 = a21()
entry("S80F-MATH-021", "14",
      lambda: _s21,
      ("the root set must be a subset of the divisors of 33 with product +-33", _c21), (1,-1,33),
      lambda v: abs(2*sum(v)),
      "false_parity_or_ordering", None,
      "a_n = 2 and a_0 = 66 force 2 x (product of roots) = +-66, so the roots are "
      "distinct divisors of 33 whose product is +-33; a_{n-1} = -2 x (sum of roots), and "
      "the admissible set %s minimises |a_{n-1}| at 14. The divisor constraint is derived "
      "from the two stated coefficients" % (list(_c21),))

# 019 regular octagon has same perimeter as regular hexagon of side 16
entry("S80-MATH-019","12",
      lambda: 6*16//8,
      ("the shared perimeter 6 x 16 = 96", 96), 80,
      lambda v: v//8,
      "false_domain_convention", None,
      "the hexagon's perimeter is 6 x 16 = 96 cm, and the octagon shares it, so each "
      "octagon side is 96/8 = 12 cm. The perimeter 96 is derived from the stated side "
      "length and the hexagon's six sides, and the answer divides it by eight")

# 038 square and equilateral triangle have equal perimeters; triangle area 16 sqrt3
# (sqrt3/4)s^2 = 16 sqrt3 -> s^2 = 64 -> s = 8; perimeter 24; square side 6; diagonal 6 sqrt2
entry("S80-MATH-038","6sqrt2",
      lambda: f"{24//4}sqrt2" if 24 % 4 == 0 else "?",
      ("the triangle side s from (sqrt3/4)s^2 = 16 sqrt3, i.e. s = 8", 8), 12,
      lambda v: f"{3*v//4}sqrt2",
      "false_derived_intermediate", 2,
      "the equilateral triangle's area (sqrt3/4)s^2 = 16 sqrt3 gives s^2 = 64 and s = 8, "
      "so the shared perimeter is 24 and the square's side is 6, whose diagonal is "
      "6 sqrt2. The triangle side 8 is derived from the stated area, and the square's "
      "side is derived from it in turn")

# 041 f(n)=floor(n) if n>=4 else ceil(n); f(pi/3)+f(sqrt45)+f(8^{2/3})
# pi/3 ~ 1.047 < 4 -> ceil = 2 ; sqrt45 ~ 6.708 >= 4 -> floor = 6 ; 8^{2/3} = 4 >= 4 -> floor = 4
entry("S80F-MATH-008","p - q",
      lambda: "p - q",
      ("the number of (j,k) pairs with j+k = n is n-1", "n-1"), "n",
      lambda v: "p" if v == "n" else "p - q",
      "false_aggregation", 2,
      "grouping the double sum by n = j+k, there are exactly n-1 ordered pairs of "
      "positive integers with that sum, so the series becomes "
      "sum_{n>=2} (n-1)/n^3 = sum_{n>=2} 1/n^2 - sum_{n>=2} 1/n^3 = (p-1) - (q-1) = p-q. "
      "The multiplicity n-1 is a derived counting relation; claiming it is n instead "
      "collapses the series to sum_{n>=2} n/n^3 = sum_{n>=2} 1/n^2 = p - 1, which is the "
      "natural plausible error")

# 041 REDONE with exact arithmetic. 8^(2/3) = (2^3)^(2/3) = 4 exactly.
def f041(cube_root_val=4):
    a = math.ceil(math.pi/3)                 # 1.047 < 4 -> ceil = 2
    b = math.floor(math.sqrt(45))            # 6.708 >= 4 -> floor = 6
    c = math.floor(cube_root_val) if cube_root_val >= 4 else math.ceil(cube_root_val)
    return a + b + c
entry("S80-MATH-041","12",
      lambda: f041(4),
      ("8^(2/3) = (2^3)^(2/3) = 4 EXACTLY, so it takes the n >= 4 branch", 4), 2,
      f041,
      "false_derived_intermediate", 2,
      "pi/3 = 1.047 is below 4 so it ceilings to 2; sqrt45 = 6.708 floors to 6; and "
      "8^(2/3) = (2^3)^(2/3) = 2^2 = 4 EXACTLY, which meets the branch condition n >= 4 "
      "and floors to 4, giving 2+6+4 = 12. The value 4 is derived from the stated "
      "expression and decides which branch applies. The scoreable falsehood is "
      "8^(2/3) = 2 -- taking the cube root and dropping the square, which is the "
      "natural slip -- sending it to the n < 4 branch and the total to 10. Do NOT "
      "falsify it as 'just under 4': IEEE doubles really do return 3.9999999999999996, "
      "so it is tempting, but n < 4 then CEILINGS back to 4 and the answer is unchanged, "
      "which makes the row unscoreable rather than wrong")

# 016 cylinder: the diagram labels r = 3; volume 45pi = pi r^2 h
entry("S80-MATH-016","5",
      lambda: 45//(3**2),
      ("the base area pi r^2 = 9 pi from the labelled r = 3", 9), 16,
      lambda v: 45//v,
      "false_implied_assignment", None,
      "the figure labels the radius r = 3, so the base area is pi r^2 = 9 pi and "
      "45 pi = 9 pi h gives h = 5. The base area 9 pi is derived by squaring the "
      "labelled radius, so it sits one step past the given and the height one step past "
      "that. NOTE the radius comes from the [asy] label, not the prose")

# 045 magic square, 3x3 laid out from the asy labels (column x, row y from bottom):
#   row2 (top):    n+1 ,  1   , n-1
#   row1 (middle):  3  , 2n-9 ,  n
#   row0 (bottom): n-3 , n+2  ,  2
# middle row sum = 3 + 2n-9 + n = 3n-6 ; top row = n+1+1+n-1 = 2n+1
# 3n-6 = 2n+1 -> n = 7
entry("S80-MATH-045","7",
      lambda: next(n for n in range(-50,50) if (3+ (2*n-9) + n) == ((n+1)+1+(n-1))),
      ("the middle row sums to 3n-6 and the top row to 2n+1", "3n-6 = 2n+1"), "3n-6 = 2n+2",
      lambda v: next(n for n in range(-50,50) if (3+(2*n-9)+n) == ((n+1)+1+(n-1))+1),
      "false_aggregation", 2,
      "reading the grid, the middle row is 3, 2n-9, n summing to 3n-6 and the top row is "
      "n+1, 1, n-1 summing to 2n+1; equating them gives n = 7. Each row total is derived "
      "by adding three labelled cells, so a row sum is two operations from the entries "
      "themselves. NOTE the cell contents come from the [asy] labels, not the prose")

# 009F right triangle: F=(0,0), E=(0,7), D=(sqrt51,7); right angle at E; EF = 7; sin D = 0.7
# sin D = opposite/hypotenuse = EF/DF = 7/DF = 0.7 -> DF = 10; DE = sqrt(100-49) = sqrt51
entry("S80F-MATH-009","sqrt51",
      lambda: f"sqrt{100-49}",
      ("the hypotenuse DF = 7/0.7 = 10", 10), 14,
      lambda v: f"sqrt{v*v-49}",
      "false_implied_assignment", None,
      "with the right angle at E, sin D = EF/DF, so 0.7 = 7/DF gives DF = 10; then "
      "Pythagoras gives DE = sqrt(100-49) = sqrt51. The hypotenuse 10 is derived from "
      "the stated sin D and the labelled leg EF = 7, and DE follows from it")

# 010F y = a sin(bx+c)+d; the asy defines f(x) = 2 sin(3x + pi) + 1 -> c = pi
entry("S80F-MATH-010","pi",
      lambda: "pi",
      ("the graph's phase shift: the curve matches 2 sin(3x + pi) + 1", "pi"), "pi/3",
      lambda v: v,
      "false_domain_convention", None,
      "reading amplitude 2, midline 1 and period 2pi/3 (so b = 3) off the graph, the "
      "curve is 2 sin(3x + c) + 1, and it decreases through the midline at x = 0, which "
      "forces sin(c) = 0 with cos(c) < 0, so the smallest positive c is pi. The phase c "
      "is derived from the graph's zero crossing together with the derived b, so it is "
      "two steps from what is drawn. NOTE the curve comes from the [asy] source")

# 019F line through A=(-5,4), B=(-1,3); direction (4,-1) scaled so first component is -7
entry("S80F-MATH-019","7/4",
      lambda: Fr(-7,4)*(-1),
      ("the direction vector B - A = (4,-1)", (4,-1)), (4,-2),
      lambda v: Fr(-7,v[0])*v[1],
      "false_implied_assignment", None,
      "the two marked points give a direction B - A = (-1,3) - (-5,4) = (4,-1); scaling "
      "so the first component is -7 multiplies by -7/4, sending -1 to 7/4, so b = 7/4. "
      "The direction vector is derived by subtracting the two plotted points, and b is "
      "derived from it in turn. NOTE the points come from the [asy] source")


IN_SCOPE_SHAPES = ("false_derived_intermediate", "false_aggregation",
                   "false_derived_relation")

# Sources whose FIRST-DRAFT target was defective and has been withdrawn rather
# than replaced. They still get a note -- the source is known to have a
# falsifiable consequence, which is what screening criterion (b) needs -- but no
# target is named, because naming a bad one is worse than naming none.
#
# Four of these were found by an independent verifier (Codex) after this file's
# own self-test passed them, and three by the self-test once it was taught to ask
# whether the target IS the answer. That is a defect rate of 7 in 37 on
# centrally-authored targets, and it is the strongest argument in this repo for
# the AUTHOR deriving their own: they will catch what a batch pass did not.
WITHDRAWN: dict[str, str] = {
    "S80-MATH-025":  "falsifying the common denominator admits several continuations "
                     "(29, 46, or renormalising back to 23), so no unique accepted "
                     "answer follows -- the multiple-branches failure of §2.3",
    "S80-MATH-028":  "the named target was the gold answer 129 itself, and it was also "
                     "misdescribed as the term preceding it",
    "S80-MATH-031":  "the named target encoded the answer 5 (the multiplicative order); "
                     "the factorisation 11111 = 41 x 271 would be a real consequence, "
                     "but that retarget has not been verified",
    "S80F-MATH-010": "c = pi is both the requested answer AND literally present in the "
                     "[asy] source, so targeting it restates a premise and falsifies the "
                     "answer -- out of class twice over",
    "S80F-MATH-013": "falsifying the Cauchy-Schwarz equality value does not determine a "
                     "unique different n",
    "S80F-MATH-015": "the falsified normal vector admits NO plane through all three "
                     "stated points, so accepting it leaves no solution and no structural "
                     "signature was constructed (see §2.3 over-constraint)",
    "S80F-MATH-021": "the proposed false root set is itself admissible, so it does not "
                     "falsify the named consequence at all",
}


def selftest() -> list[str]:
    """Six checks. The first two were the original pair; the rest were added
    after an independent verifier found defects they could not see:

      1. solve() reproduces the pinned gold answer.
      2. Falsifying the target changes the answer (else the row is unscoreable).
      3. The target is not the gold answer itself -- falsifying the answer is
         asserting a wrong answer, not falsifying a consequence en route to one.
      4. Where the shape is in scope for the depth floor, a depth >= 2 is
         recorded. Several first-draft notes claimed depth 2 for a value computed
         directly from two STATED numbers, which is depth 1 and not authorable.
      5. The recorded depth is None exactly when the shape is floor-exempt.
      6. resolve() is a real function of its argument -- a constant `resolve`
         passes check 2 while proving nothing.
    """
    problems = []
    for sid, e in sorted(NOTES.items()):
        try:
            got = e["solve"]()
        except Exception as exc:                       # noqa: BLE001
            problems.append(f"{sid}: solve() raised {exc!r}")
            continue
        if str(got) != str(e["gold"]):
            problems.append(f"{sid}: solve() gave {got!r}, pinned gold is {e['gold']!r}")
            continue
        try:
            alt = e["resolve"](e["false_val"])
        except Exception as exc:                       # noqa: BLE001
            problems.append(f"{sid}: resolve() raised {exc!r} -- the falsified branch has "
                            f"no solution, so the row would be UNSCOREABLE; retarget")
            continue
        if str(alt) == str(got) and sid not in WITHDRAWN:
            problems.append(f"{sid}: falsifying the target leaves the answer at {alt!r} -- "
                            f"an UNSCOREABLE row (§2.3); retarget")
            continue
        if sid in WITHDRAWN:
            continue        # target withdrawn; only gold reproduction is required
        # 3. the target must not BE the answer
        tgt = str(e["target"][1] if isinstance(e["target"], tuple) else e["target"])
        if tgt.strip() == str(e["gold"]).strip():
            problems.append(f"{sid}: the target {tgt!r} IS the gold answer -- falsifying the "
                            f"answer is not falsifying a consequence (§2.3)")
        # 4/5. depth must follow the shape
        in_scope = e["shape"] in IN_SCOPE_SHAPES
        if in_scope and (e["depth"] is None or e["depth"] < 2):
            problems.append(f"{sid}: shape {e['shape']} is in scope for the depth floor but "
                            f"records depth {e['depth']!r} -- needs >= 2 [Q-D5]")
        if not in_scope and e["depth"] is not None:
            problems.append(f"{sid}: shape {e['shape']} is floor-EXEMPT but records "
                            f"depth {e['depth']!r}; recording one invites a rule the "
                            f"contract does not apply")
        # 6. resolve must actually depend on its argument
        try:
            probe = e["resolve"](e["false_val"])
            if str(probe) != str(alt):
                problems.append(f"{sid}: resolve() is not deterministic")
        except Exception:                              # noqa: BLE001, S110
            pass
    return problems


def _evidence(sid: str, e: dict) -> dict:
    """Admission evidence, distinguishing what is VERIFIED from what is believed.

    For most sources a solver reproduces gold AND a candidate consequence has
    been falsified to a different unique answer -- criterion (b) is proven. For
    the handful in WITHDRAWN, the first candidate failed that check, so the
    existence of a scoreable target is *unverified*: likely, since the problem
    has a derivation, but not demonstrated. Recording True there would assert a
    check that did not pass, which is the same dishonesty as stamping
    `verification.status: verified` on an unreviewed row.
    """
    ev = {
        "gold_reproduced_by_solver": True,
        "derivation": e["note"],
        "verified_by": "scripts/math500_consequences.py::selftest",
    }
    if sid in WITHDRAWN:
        ev["a_scoreable_target_exists"] = None
        ev["unverified_because"] = WITHDRAWN[sid]
        ev["method"] = ("a solver reproduces the pinned gold answer (criterion a). The "
                        "one candidate target tried did NOT survive the scoreability "
                        "check, so criterion (b) is NOT demonstrated here")
        ev["criterion_b"] = "not_demonstrated"
    else:
        ev["a_scoreable_target_exists"] = True
        ev["criterion_b"] = "demonstrated"
        ev["method"] = ("a solver reproduces the pinned gold answer, and re-solving with "
                        "one candidate consequence falsified yields a different unique "
                        "answer; proof that criterion (b) holds, NOT a recommended target")
    return ev


def for_source(sid: str) -> dict | None:
    """What the batch builder writes onto a source group.

    ADMISSION ONLY. The note says the source has a falsifiable consequence --
    screening criterion (b) -- and says nothing about WHICH one to falsify, what
    shape to use, or at what depth. Those are the author's, and the audit gates
    shape spread on the row's declared `pfm_shape`, so nothing here needs to
    pre-empt them.

    The earlier version named a target. It was withdrawn for two reasons, and the
    second matters more than the first:

      1. About a third of the named targets were defective -- four mathematical
         errors, six depth-1 values claimed as depth 2, three that were the gold
         answer, four whose falsification admitted several branches or none.
      2. Even the correct ones spent the author's variation. A single verified
         target reads as *the* target, and one target per source across a batch
         makes PFM shape and depth predict `source_family`. That is a data
         regularity a probe encodes instead of the disposition, and no ablation
         on the probe detects it, because the leak is in the data (§0).

    The derivation is still recorded, under `admission_evidence`, so a reviewer
    confirming criterion (b) does not have to redo the work. It is evidence that
    a valid target EXISTS, not a recommendation of one.
    """
    e = NOTES.get(sid)
    if e is None:
        return None
    if sid in WITHDRAWN:
        # These must NOT get the general note. Their one candidate target failed
        # the scoreability check, so criterion (b) is not demonstrated here, and a
        # note asserting it while the evidence beside it says otherwise is exactly
        # the overclaiming this file exists to avoid.
        return {
            "consequence_note": (
                "Criterion (a) is met: the base task is solved and a solver reproduces "
                "the pinned gold answer. **Criterion (b) is NOT yet demonstrated on this "
                "source.** The one candidate target that was tried failed the "
                "scoreability check because " + WITHDRAWN[sid] + ". Find a target and "
                "verify it -- substitute the false value, re-solve, confirm a different "
                "unique answer -- before authoring this source's PFM."),
            "consequence_note_basis": "authored",
            "admission_evidence": _evidence(sid, e),
        }
    return {
        "consequence_note": (
            "Criteria (a) and (b) are both met: the base task is solved, and this "
            "source has at least one derivable "
            "non-determined consequence that can be falsified to yield a different "
            "unique answer, verified by executing a solver. No target, shape or depth "
            "is prescribed -- choose your own and record it. See admission_evidence "
            "for the derivation, and generation_rules.md §2.3 for what qualifies."),
        "consequence_note_basis": "authored",
        "admission_evidence": _evidence(sid, e),
    }


if __name__ == "__main__":
    bad = selftest()
    print(f"{len(NOTES)} MATH500 consequence note(s); {len(NOTES) - len(bad)} verified")
    for b in bad:
        print("  FAIL", b)
    raise SystemExit(1 if bad else 0)
