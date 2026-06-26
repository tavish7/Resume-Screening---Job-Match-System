"""ResBot's brain: a small LangGraph state machine.

Flow: route the message, then either answer as the persona, refuse (bias/off-topic),
or go down the text-to-SQL path. The SQL path runs the query and, if SQLite throws,
asks the model to repair it - up to MAX_SQL_RETRIES times - before giving up.
"""
from functools import lru_cache
from typing import TypedDict

from langgraph.graph import StateGraph, END

from . import prompts
from .config import MAX_SQL_RETRIES
from .db import run_sql, schema_text, suitability_values
from .llm import ask


class State(TypedDict, total=False):
    question: str
    route: str
    sql: str
    cols: list
    rows: list
    error: str
    retries: int
    answer: str


def _clean_sql(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text.strip("`")
        text = text.replace("sql", "", 1) if text.lower().startswith("sql") else text
    return text.strip().rstrip(";").strip()


def _as_table(cols, rows, max_rows=30):
    if not rows:
        return "(no rows)"
    head = " | ".join(cols)
    body = "\n".join(" | ".join("" if v is None else str(v) for v in r) for r in rows[:max_rows])
    extra = f"\n... ({len(rows) - max_rows} more rows)" if len(rows) > max_rows else ""
    return f"{head}\n{body}{extra}"


def route_node(state: State):
    route = ask([("human", prompts.ROUTER.format(question=state["question"]))]).lower()
    for r in ("bias", "off_topic", "generic", "data"):
        if r in route:
            return {"route": r}
    return {"route": "data"}


def generic_node(state: State):
    reply = ask([("system", prompts.PERSONA), ("human", state["question"])])
    return {"answer": reply}


def bias_node(state: State):
    return {"answer": prompts.BIAS_REFUSAL}


def off_topic_node(state: State):
    return {"answer": prompts.OFF_TOPIC}


def gen_sql_node(state: State):
    system = prompts.SQL_SYSTEM.format(
        schema=schema_text(), suitability=", ".join(suitability_values())
    )
    sql = _clean_sql(ask([("system", system), ("human", state["question"])]))
    return {"sql": sql, "retries": 0}


def exec_sql_node(state: State):
    try:
        cols, rows = run_sql(state["sql"])
        return {"cols": cols, "rows": rows, "error": ""}
    except Exception as exc:
        return {"error": str(exc)}


def fix_sql_node(state: State):
    fixed = ask([
        ("system", prompts.SQL_SYSTEM.format(
            schema=schema_text(), suitability=", ".join(suitability_values()))),
        ("human", prompts.SQL_FIX.format(sql=state["sql"], error=state["error"])),
    ])
    return {"sql": _clean_sql(fixed), "retries": state.get("retries", 0) + 1}


def summarize_node(state: State):
    table = _as_table(state.get("cols", []), state.get("rows", []))
    reply = ask([
        ("system", prompts.PERSONA),
        ("human", prompts.SUMMARIZE.format(
            question=state["question"], n=len(state.get("rows", [])), table=table)),
    ])
    return {"answer": reply}


def giveup_node(state: State):
    return {"answer": "I tried a few times but couldn't pull that from the data. "
                      "Could you rephrase the question?"}


def _route_choice(state: State):
    return state["route"]


def _after_exec(state: State):
    if not state.get("error"):
        return "summarize"
    return "fix" if state.get("retries", 0) < MAX_SQL_RETRIES else "giveup"


@lru_cache(maxsize=1)
def _compiled():
    g = StateGraph(State)
    g.add_node("route", route_node)
    g.add_node("generic", generic_node)
    g.add_node("bias", bias_node)
    g.add_node("off_topic", off_topic_node)
    g.add_node("gen_sql", gen_sql_node)
    g.add_node("exec_sql", exec_sql_node)
    g.add_node("fix_sql", fix_sql_node)
    g.add_node("summarize", summarize_node)
    g.add_node("giveup", giveup_node)

    g.set_entry_point("route")
    g.add_conditional_edges("route", _route_choice, {
        "data": "gen_sql", "generic": "generic", "bias": "bias", "off_topic": "off_topic",
    })
    g.add_edge("generic", END)
    g.add_edge("bias", END)
    g.add_edge("off_topic", END)
    g.add_edge("gen_sql", "exec_sql")
    g.add_conditional_edges("exec_sql", _after_exec, {
        "summarize": "summarize", "fix": "fix_sql", "giveup": "giveup",
    })
    g.add_edge("fix_sql", "exec_sql")
    g.add_edge("summarize", END)
    g.add_edge("giveup", END)
    return g.compile()


def answer(question):
    """Run the graph and hand back the answer plus what it did (for transparency)."""
    final = _compiled().invoke({"question": question})
    return {
        "answer": final.get("answer", ""),
        "route": final.get("route", ""),
        "sql": final.get("sql", ""),
        "cols": final.get("cols", []),
        "rows": final.get("rows", []),
        "retries": final.get("retries", 0),
    }
