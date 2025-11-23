from graphviz import Digraph

# Graph creation
arch = Digraph("AIgent-Architecture", format="png")
arch.attr(rankdir="TB")  # top-down

# Styles
arch.attr("node", shape="rectangle", style="filled", color="black")
AGENT_STYLE = {"fillcolor": "#FCFC58"}
MCP_STYLE = {"fillcolor": "#B7B7B7"}
TOOL_STYLE = {"shape": "ellipse", "fillcolor": "#94DAA1"}
START_END_STYLE = {"shape": "ellipse", "fillcolor": "#B3F0FF"}

# -------------------
# Nodes
# -------------------

# Start / End
arch.node("__start__", "__start__", **START_END_STYLE)
arch.node("__end__", "__end__", **START_END_STYLE)

# Agents
agents = [
    "Fetcher Agent",
    "Grid Agent",
    "Battery Agent",
    "Compute Agent",
    "Forecast Agent",
    "Price-Per-Inference Calculator",
    "Spikes Detector Agent",
    "Renewable-Only Detector Agent",
    "Battery Charger Agent",
    "Datacenter Caller Agent",
    "Deciding Agent",
    "Defering Agent",
    "Deviation Volume Calculator Agent",
    "Flexibility Market Trader",
    "Remuneration Agent",
    "Self-Remuneration Agent",
]
for a in agents:
    arch.node(a, a, **AGENT_STYLE)

# Tools
tools = ["ML Forecast Model", "Sum Grids", "PPI Calculator", "Optimiser", "Deviation Volume Calculator Tool"]
for t in tools:
    arch.node(t, t, **TOOL_STYLE)

# MCPs
mcps = [
    "Web (Grid data)",
    "B.P.P.",
    "B.A.P.",
    'Beckn "Charge Batteries"',
    'Beckn "Search Available Datacenters"',
    'Beckn "Defer Workload"',
    "Wholesale Elec. Market",
    "B.A.P. (Remuneration)",
    "Bank Account (our bank)",
    "Firebase DB"
]
for m in mcps:
    arch.node(m, m, **MCP_STYLE)

# -------------------
# Edges (handoffs)
# -------------------

# __start__ -> Fetcher
arch.edge("__start__", "Fetcher Agent")

# Fetcher -> 3 agents
arch.edge("Fetcher Agent", "Grid Agent")
arch.edge("Fetcher Agent", "Battery Agent")
arch.edge("Fetcher Agent", "Compute Agent")

# Fetcher -> Forecast & Datacenter Caller
arch.edge("Fetcher Agent", "Forecast Agent", label="non-deferable CW")
arch.edge("Fetcher Agent", "Datacenter Caller Agent", label="deferable CW")

# Grid/Battery/Compute -> Fetcher (retour)
arch.edge("Grid Agent", "Fetcher Agent", label="elec. price, carbone intensity")
arch.edge("Battery Agent", "Fetcher Agent", label="batteries info")
arch.edge("Compute Agent", "Fetcher Agent", label="compute workloads (CW)")

# MCP connections
arch.edge("Web (Grid data)", "Grid Agent", dir="both")
arch.edge("B.P.P.", "Battery Agent", dir="both")
arch.edge("B.A.P.", "Compute Agent", dir="both")
arch.edge('Beckn "Charge Batteries"', "Battery Charger Agent", dir="both")
arch.edge('Beckn "Search Available Datacenters"', "Datacenter Caller Agent", dir="both")

# Forecast -> ML Forecast Model
arch.edge("Forecast Agent", "ML Forecast Model", style="dotted", dir="both")

# Forecast -> PPI Calculator
arch.edge("Forecast Agent", "Price-Per-Inference Calculator", label="non-deferable CW pred.")

# PPI Calculator -> tools
arch.edge("Price-Per-Inference Calculator", "Sum Grids", style="dotted", dir="both")
arch.edge("Price-Per-Inference Calculator", "PPI Calculator", style="dotted", dir="both")

# PPI Calculator -> Spikes & Renewable-Only Detector
arch.edge("Price-Per-Inference Calculator", "Spikes Detector Agent", label="price curve")
arch.edge("Price-Per-Inference Calculator", "Renewable-Only Detector Agent")

# Renewable-Only -> Battery Charger
arch.edge("Renewable-Only Detector Agent", "Battery Charger Agent")

# Battery Charger -> PPI Calculator (feedback)
arch.edge("Battery Charger Agent", "Price-Per-Inference Calculator")

# Spikes & Renewable -> DC Caller
arch.edge("Spikes Detector Agent", "Datacenter Caller Agent", label='cheap/expensive slots')
arch.edge("Renewable-Only Detector Agent", "Datacenter Caller Agent")

# DC Caller -> Deciding -> Defering -> Deviation Calc -> Trader -> Remuneration -> Self-Remuneration -> __end__
arch.edge("Datacenter Caller Agent", "Deciding Agent")
arch.edge("Deciding Agent", "Optimiser", style="dotted", dir="both")
arch.edge("Deciding Agent", "Defering Agent", label='instructions list')
arch.edge("Defering Agent", 'Beckn "Defer Workload"', dir="both")
arch.edge("Defering Agent", "Deviation Volume Calculator Agent")
arch.edge("Deviation Volume Calculator Agent", "Deviation Volume Calculator Tool", style="dotted", dir="both")
arch.edge("Deviation Volume Calculator Agent", "Flexibility Market Trader")
arch.edge("Flexibility Market Trader", "Wholesale Elec. Market", dir="both", label='P415')
arch.edge("Flexibility Market Trader", "Remuneration Agent", label='contracts')
arch.edge("Remuneration Agent", "B.A.P. (Remuneration)", dir="both")
arch.edge("Remuneration Agent", "Self-Remuneration Agent")
arch.edge("Self-Remuneration Agent", "Bank Account (our bank)", dir="both")
arch.edge("Self-Remuneration Agent", "__end__")

# -------------------
# Logging Hub à l'écart en bas à droite
# -------------------
with arch.subgraph() as s:
    s.attr(rank="same")  # même niveau
    s.node("Logging Hub Agent", "Logging Hub Agent", **AGENT_STYLE)
    s.edge("Logging Hub Agent", "Firebase DB", dir="both")


with arch.subgraph(name="cluster_legend") as l:
    l.attr(label="Legend", color="black", style="dashed")
    l.node("Legend Agent", "Agent", **AGENT_STYLE)
    l.node("Legend Tool", "Tool", **TOOL_STYLE)
    l.node("Legend MCP", "MCP Server", **MCP_STYLE)
    l.node("Legend StartEnd", "Start / End", **START_END_STYLE)


# -------------------
# Render graph
# -------------------
arch.render("architecture_graph", view=True)
print("Graph generated: architecture_graph.png")
