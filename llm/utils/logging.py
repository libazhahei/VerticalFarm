from enum import Enum


ANSI_COLORS = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
}

ANSI_STYLES = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "normal": "22",
}


def ansi_cprint(text: str, fg: str = "green", bg: str | None = None, style: str = "normal", end: str = "\n") -> None:
    fg_code = ANSI_COLORS.get(fg.lower(), "37")
    style_code = ANSI_STYLES.get(style.lower(), "0")
    bg_code = ""
    if bg:
        bg_code = ANSI_COLORS.get(bg.lower(), "")
        if bg_code:
            bg_code = str(int(bg_code) + 10)

    ansi_sequence = f"\033[{style_code};{fg_code}"
    if bg_code:
        ansi_sequence += f";{bg_code}"
    ansi_sequence += "m"
    reset_sequence = "\033[0m"
    print(f"{ansi_sequence}{text}{reset_sequence}", end=end)


class WorkflowStage(str, Enum):
    PLAYBOOK = "[1] Playbook RAG"
    DIAGNOSIS = "[2] Diagnosis"
    CANDIDATES = "[3] Candidates"
    SIDE_EFFECTS = "[4] Side Effects"
    SAFETY_SHIELD = "[5] Safety Shield"
    SIMULATION = "[6] Simulation"
    DECISION = "[7] Decision"
    FINAL_COMMAND = "[8] Final MQTT Command"


class WorkflowLogger:
    def __init__(self) -> None:
        self._history: list[tuple[WorkflowStage, str]] = []

    def stage(self, stage: WorkflowStage, message: str) -> None:
        line = f"{stage.value}: {message}"
        self._history.append((stage, message))
        ansi_cprint(line, fg="green", style="bold")

    def detail(self, message: str, fg: str = "cyan") -> None:
        ansi_cprint(f"  {message}", fg=fg)

    def warn(self, message: str) -> None:
        ansi_cprint(f"  {message}", fg="yellow")

    def error(self, message: str) -> None:
        ansi_cprint(f"  {message}", fg="red")

    @property
    def history(self) -> list[tuple[WorkflowStage, str]]:
        return list(self._history)
