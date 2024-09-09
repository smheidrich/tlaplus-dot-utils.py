import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from os import getenv
from sys import stdin
from textwrap import dedent, indent
from typing import IO, Any

latex: bool = bool(getenv("TLAPLUS_D2_LATEX", False))
state_as_boxes: bool = bool(getenv("TLAPLUS_D2_STATE_AS_BOXES", True))


@dataclass
class State:
  id: int
  label_tlaplus: str

  @property
  def label_latex(self) -> str:
    # TODO Surely there is a way to use TLA+'s own LaTeX-output
    #  programmatically somehow so we don't have to do this?
    return (
      self.label_tlaplus.replace("/\\", "\\land")
      .replace(r"\/", "\\lor")
      .replace("|->", "\\mapsto")
      .replace("\n", " \\\\ ")
      .replace("FALSE", "\\mathrm{FALSE}")
      .replace("TRUE", "\\mathrm{TRUE}")
      .replace('"', '\\text{"}')  # these look like garbage otherwise
    )


@dataclass
class Step:
  id: int
  action_name: str
  from_state_id: int
  to_state_id: int
  color_id: str


def parse_and_write_d2(infile: IO[Any], outfile: IO[str]) -> None:
  # Shortcut:
  writeln: Callable[[str], Any] = lambda s: outfile.write(f"{s}\n")

  # Parse JSON
  d = json.load(stdin)

  # Check metadata version
  try:
    version_str = d["metadata"]["format"]["version"]
    version = tuple(int(x) for x in version_str.split("."))
    if len(version) < 3:
      version = (*version, 0)
  except Exception as e:
    raise ValueError(
      "Couldn't determine format version (see errors above)"
    ) from e
  if not (0, 1, 0) <= version < (0, 2, 0):
    raise ValueError(f"Can't handle format version {version_str}")

  # Construct dataclass instances
  states = [
    State(
      id=state_d["id"],
      label_tlaplus=state_d["labelTlaPlus"],
    )
    for state_d in d["states"]
  ]
  steps = [
    Step(
      id=step_d["id"],
      action_name=step_d["actionName"],
      from_state_id=step_d["fromStateId"],
      to_state_id=step_d["toStateId"],
      color_id=step_d["colorId"],
    )
    for step_d in d["steps"]
  ]

  # Output as D2
  for state in states:
    # States
    if latex:
      label = repr(state.label_latex)[1:-1]
      writeln(
        dedent(
          f"""\
            state{state.id}: "" {{
                equation: |latex
                    \\\\displaylines {{
                        {indent(label, "    ")}
                    }}
                    % add some spacing (otherwise it messes up)
                    \\\\ \\\\ \\\\ \\\\ \\\\ \\\\
                |
            }}
            """
        )
      )
    elif state_as_boxes:
      from tlaplus_dot_utils.state_parsing import tlaplus_state_to_dataclasses
      from tlaplus_dot_utils.state_to_d2 import dataclasses_state_to_d2

      state_boxes = dataclasses_state_to_d2(
        tlaplus_state_to_dataclasses(state.label_tlaplus)
      )
      writeln(
        dedent(
          f"""\
            state{state.id}: "" {{
                {indent(state_boxes, "    ")}
            }}
            """
        )
      )
    else:
      label = repr(state.label_tlaplus).replace('"', '\\"')
      label = f'"{label[1:-1]}"'
      writeln(f"state{state.id}: {label}")

  writeln("")

  # Steps
  color_id_to_color = defaultdict(
    lambda: "black",
    {
      "0": "red",
      "1": "blue",
      "2": "green",
      "3": "orange",
      "4": "purple",
      "5": "cyan",
    },
  )
  for step in steps:
    label = repr(step.action_name)
    label = f'"{label[1:-1]}"'
    writeln(
      f"state{step.from_state_id} -> state{step.to_state_id}: {label} {{"
    )
    writeln("  style: {")
    writeln(f"     stroke: {color_id_to_color[step.color_id]}")
    writeln("  }")
    writeln("}")
