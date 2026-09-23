# Manuscript changes since the arXiv version

Base: **`fdd2e0d`**, "Import the arXiv version of the manuscript from Overleaf" (2026-09-15).
Compiled here against `HEAD` on 2026-09-22; updated on 2026-09-23 for the register pass (§7)
and the revived Kowalski paragraph (§2).

The commits concerned are `git log fdd2e0d..HEAD -- docs/paper/`. Net, as of 2026-09-23:
`main.tex` **+75 / −52** lines, plus one new generated figure and the script that generates it.

**These changes exist only in git. Overleaf still holds the arXiv text.** This file is the
inventory for carrying them across; a mechanical diff is described at the end.

Everything here follows the standing rule (`KNOWN_ISSUES.md` §G): where the code and the
manuscript disagreed, the *code* changed and the manuscript was only corrected where it stated
something that was never true, or described a mechanism that has since been fixed.

---

## 1. New figure — replaces `fig:origin`

| file | status |
| --- | --- |
| `graphic/origin-resolution.pdf` | **new**, included by `main.tex` |
| `graphic/origin-resolution.png` | **new**, for viewing only |
| `graphic/origin_resolution_figure.py` | **new**, 346 lines — generates both |
| `graphic/origin-decision-tree-highlighted.png` | **no longer included** (still in the tree) |

```latex
-\includegraphics[width=1.1\linewidth]{graphic/origin-decision-tree-highlighted.png}
+\includegraphics[width=0.95\linewidth]{graphic/origin-resolution.pdf}
```

The figure is now **generated, not drawn**, which is the point of the change as much as the
content is: the image it replaces was an export from a mind-mapping tool, so every correction
meant reopening that tool — which is why the image and its caption had drifted apart. The script
checks its own text for overflow and refuses to write a figure that does not fit.

**The caption is rewritten in full**, and this is the single largest prose change in the set. It
used to license reading any option as either a time or a value origin; it now states that the two
slots ask different questions, that `"anchor"`, `"last"` and a context name are refused in the
value slot because each would answer in the wrong physical units, and that the intended reading
is expressible as a pair — `origin=["molasses", "variable"]`.

**Carrying this over means uploading the two image files and the script**, not just the text.

---

## 2. Substantive prose — new passages

Nine passages are new: six whole paragraphs, and three sentences added to existing ones
(`ramp` and `anchor` live inside `sec:functions` and `sec:anchor`; there is no `sec:ramp`). Each
states behaviour that the package now enforces and the manuscript did not describe. The openings
quoted are those after the register pass of §7.

| § | passage | why |
| --- | --- | --- |
| `sec:functions` | "Any other keyword is read as the name of a variable…" — one sentence, closing the paragraph after the `create` signature | the positional input forms were withdrawn (`093c05f`) |
| `sec:functions` | **"What a ramp refuses"** — a whole paragraph, three sentences | zero and negative durations now raise; a flat ramp is a hold and is kept; a ramp of an unset variable raises (`dcda171`) |
| `sec:anchor` | "Note that `t` is required…" + a two-line `minted` example | `t` became required; the two idioms differ by ~0.1 s in the paper's own demo from `optical_pumping` onwards (`771f5d3`) |
| `sec:stacking` | "The two take their stages differently…" | `stack` takes stages already called, `cascade` takes them bare — nothing in the syntax said so (`2b5bca1`) |
| `sec:stacking` | "`MOT` also takes a `timeline` argument…" — three sentences, closing the paragraph after the `MOT` listing | a stage must declare what it forwards, rather than collecting it in `**kwargs` (`19d41ad`) |
| `sec:stacking` | "Routing is strict…" | `cascade` now refuses a keyword it cannot place (`93796b7`) |
| `sec:interweaving` | "This gives a practical criterion for what a stage should declare…" | when a stage takes `origin` and when it should not |
| `sec:adwin` | "The arrays uploaded to the controller are prepared in the same spirit…" — after the event-loop paragraph | `drop_repeats` (`84f2ef1`) does on the controller's cycle grid what Kowalski *et al.* do by timing transitions at DAC-code changes. The arXiv text had this as future work, commented out at the end of `sec:discussion`; **that commented line is deleted**, and the paragraph is rewritten in the present tense where the conversion is described |
| `sec:forwarding` | "Only these three functions accept arbitrary keywords…" — one sentence, closing the "Keyword forwarding provides a third way" paragraph | `**kwargs` is confined to the `default_state` path |

---

## 3. Corrected claims

These were **wrong in the arXiv version**, not merely incomplete.

**`sec:origin`, the default.** Said the reference point is the most recent anchor, "and the most
recent entry otherwise". The list is a *terminal chain*: failing both — as on an empty timeline —
entries are placed in absolute time **with a warning**. Added.

**`sec:origin_full`, the value-relative default.** Said that *no* default in the package is
value-relative. `ramp`'s start point always was, and must be, or ramps would not chain. The
passage now gives `ORIGIN__DEFAULTS__RAMP` as `[["anchor", "variable"], ["last", "variable"]]`
and says why. This is the correction with the most physics behind it.

**`sec:origin_full`, `origin2`'s default.** Shown as `["variable"]`; it is `["variable", 0.0]`.
The text now says the value slot refers to nothing at all, because a ramp's end value is always
stated.

**`sec:origin_full`, `"last"`.** Described as usable for "time or value". Value is now refused.

**`sec:adwin`, the event-loop cost.** "one comparison per channel group" → "**two** comparisons".
The ADbasic listing gained the index bound that `790528e` added:

```basic
-  if (data_10[analogIdx] = cc) then
+  if ( (analogIdx <= analogArrayDim) and (data_10[analogIdx] = cc) ) then
```

(and the same for `data_20`/`digitalIdx`). The listing is again line-for-line identical to
`resources/ADwin/WignerTimeADwin.bas`. The argument the sentence supports is unaffected: no
arithmetic is added and the cost is still independent of how many ramps are in flight.

**`sec:demonstration`, the device table.** The conversion factors were wrong by a factor of 5 —
`1/2.0` where the text's own reasoning gives `10/5.0`, and `1/3.0` for `10/3.0`. Corrected in the
table, and a sentence added stating the rule: *a linear conversion is the factor taking the unit
**to** volts.*

**`sec:devicelayer`, the naming convention.** "a particular regex, defined within the `variable`
module" → "configurable as `config.VARIABLE__REGEX`". The convention became a rebindable default.

**`sec:forwarding`, how far `**kwargs` travels.** Said "every stage between a call site and
`default_state` forwards `**kwargs`". Only `init` and `finish` do now, and deliberately.

---

## 4. Signatures

All six signatures the manuscript shows now agree with the code.

```diff
-def create( *vtvc, t=0.0, context=None, **vtvc_dict )
+def create( t=0.0, context=None, **vtvc_dict )

-def stack( timeline_or_f: wt_frame.CLASS | Callable, *fs: list[Callable], **kws )
+def stack( timeline_or_f: wt_frame.CLASS | Callable, *fs: Callable, **kws )

-def cascade( *fs: list[Callable], **kws )
+def cascade( *fs: Callable, **kws )
```

`ramp`: `t2` moved ahead of `context`/`origin` to match the code's parameter order, and
`origin2=["variable"]` → `origin2=["variable", 0.0]`.

`tab:inputSpecs`'s caption no longer advertises the positional forms as available for
programmatic use. After the register pass (§7) it simply refers to the API documentation; before
it, it said that the package uses those forms internally when expanding a ramp.

---

## 5. The demo listing — `**kwargs` → `timeline=None`

The largest mechanical change, touching every stage shown: `MOT`, `MOT_detuned_growth`,
`MOT_off`, `molasses`, `optical_pumping`, `magnetic_trapping`, `pull_coils`, `trigger_camera`.

```diff
-def MOT(duration=15, lower_current=-1.0, upper_current=-0.98, origin=0.0, **kwargs):
+def MOT(duration=15, lower_current=-1.0, upper_current=-0.98, origin=0.0, timeline=None):
```

`trigger_camera` changes more than the others — it gains `context` and `origin` explicitly, and
its misspelt `exposition` parameter becomes `exposure` (the body already used `exposure`, so the
listing as published does not run).

`pull_coils` gains `t=None, context=None` alongside `timeline=None`.

---

## 6. Still outstanding — *not* in this diff

- **D7 / #121**, the `__` convention: the demo listing's parameter names still differ between the
  paper's single-underscore style and the package's `__`. Undecided, so untouched.
- **#133 / D18**: `sec:adwin` claims channel availability is a question of which modules are
  installed. The backend writes every digital update to module 1, so a second digital module is
  unaddressable. The claim needs either a code fix or a qualifying sentence.
- **The 1 µs claim** (`sec:intro`, the “Fast” paragraph, and `sec:adwin`) is quoted, not
  verified. See `KNOWN_ISSUES.md` D21.
- **The revived Kowalski paragraph** (§2) describes what the package uploads; `drop_repeats` has
  not yet run on the rig.

---

## 7. Register and typography pass (2026-09-23)

The prose added since the arXiv version had been written as developer notes: too long, and using
vocabulary a physicist does not know ("namespace", "positional", "placement argument", "call site",
"terminal chain"). It also recounted behavior the package used to have. The passages of §2 were
rewritten to the rules now kept in `WRITING.md` at the repository root. The main cuts:

- **"What a ramp refuses"** goes from eight sentences to three. The account of what a negative
  duration used to do, and the note about which filter removes a hold's redundant rows, are gone.
- **"Routing is strict"** goes from four sentences to two. The matching rules are replaced by the
  demo's own case: `MOT` begins `MOT_detuned_growth`.
- The `create` and `sec:forwarding` additions each shrink to a single sentence, and the
  `tab:inputSpecs` caption no longer mentions an internal input form.

Typography was brought into line with the rest of the manuscript: `--` and `—` became `–`,
straight apostrophes became `’`, and `\(\sim0.1\,\)s` became "about 0.1\,s".

**Carrying this across touches text Overleaf already has**, not only text it lacks. These are edits
to arXiv sentences, so a diff against Overleaf will show them:

| where | change |
| --- | --- |
| Acknowledgements | `Anthropic's` → `Anthropic’s` |
| `sec:forwarding`, first paragraph | `--` → `–` (twice) |
| `sec:forwarding`, "Keyword forwarding provides a third way" | "keyword namespace *is* the variable namespace" → "reads any keyword it does not itself recognize as a variable"; "terminal" → "final"; "initialises" → "initializes" (this paragraph was already in §3) |
| `sec:forwarding`, "The three keywords given in…" | `--` → `–` |
| `sec:forwarding`, "Nothing here is a library feature" | "keeps one namespace deliberately open: the terminal `**vtvc_dict`" → "`create`, `update` and `ramp` deliberately read any keyword they do not recognize as a variable"; "terminal call" → "final `create` or `update` call"; "rather than raising" → "rather than raising an error"; `--` → `–` (twice) |

The `sec:forwarding` appendix is where "namespace" first entered the manuscript. It was already
there in the arXiv version.

---

## Producing a mechanical diff

No LaTeX toolchain is installed in the development environment here, so this has not been
compiled. To produce a marked-up PDF where a toolchain exists:

```bash
git -C <repo> show fdd2e0d:docs/paper/main.tex > /tmp/main-arxiv.tex
cd docs/paper
latexdiff /tmp/main-arxiv.tex main.tex > main-diff.tex
pdflatex -shell-escape main-diff.tex     # minted needs -shell-escape and pygmentize
```

`latexdiff` ships with TeX Live and MiKTeX. Note that it handles `minted` blocks as whole-block
replacements rather than word by word, so §5 above will show as large deleted/inserted listings
rather than as the one-word changes they are — which is the main reason this file exists.

For the text alone, without a toolchain:

```bash
git diff --word-diff --color-words fdd2e0d..HEAD -- docs/paper/main.tex
```
