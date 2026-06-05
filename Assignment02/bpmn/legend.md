# BPMN → Simulation Parameter Legend (HPC Cluster Scheduler)

One-page mapping of every BPMN element in [hpc-bpmnio.bpmn](hpc-bpmnio.bpmn) to its
Kendall's-notation / simulation meaning and to the implementation in
[queue_model.py](../queue_model.py).

## Kendall's notation per queueing node — `A / S / c / N / D`

| Symbol | Meaning | Code field (`QueueModel`) |
|--------|---------|---------------------------|
| `A`    | Arrival-time distribution (M = exponential, D = deterministic, G = general) | `arrival_dist` |
| `S`    | Service-time distribution | `service_dist` |
| `c`    | Number of servers / compute slots | `servers` |
| `N`    | System capacity (blocking when full; omit ⇒ infinite) | `capacity` |
| `D`    | Queue discipline (FIFO / LIFO / SIRO) | `discipline` |

## BPMN element → simulation mapping

| BPMN element (id) | Diagram symbol | Simulation meaning |
|-------------------|----------------|--------------------|
| Pool `Participant_HPC` | Pool | The whole HPC cluster scheduler model |
| Lane `Lane_Standard` | Lane | Standard partition / queueing node `{A_std, S_std, c_std, N_std, D_std}` |
| Lane `Lane_Priority` | Lane | Priority partition / queueing node `{A_pri, S_pri, c_pri, N_pri, D_pri}` |
| `StartEvent_Job` | Start event | Exogenous job arrivals; distribution `A`, rate `λ` (annotation `TA_Arrival`) |
| `DataObjectReference_Meta` | Data object | Job metadata carried by each entity (class, length, requested cores) → `entity` dict |
| `Gateway_Priority` | Exclusive gateway | Class routing: `Yes` = priority with prob `p`, `No` = standard with prob `1 − p` |
| `Task_Allocate` | Task | Resource allocation: acquire nodes/cores before execution |
| `Task_Execute_Pri` | Task | Priority service, distribution `S_pri` on `c_pri` servers |
| `Task_Execute_Std` | Task | Standard service, distribution `S_std` on `c_std` servers |
| `EndEvent_Done_Pri` / `EndEvent_Done_Std` | End event | Job completion; resources released, entity leaves the node |

## Routing probabilities (Gateway `Gateway_Priority`)

| Flow | Annotation | Probability |
|------|-----------|-------------|
| `Flow_Gateway_Yes` → priority lane | `TA_PriProb` | `p` |
| `Flow_Gateway_No` → standard lane | `TA_StdProb` | `1 − p` |

## Capacity / blocking rules

| Node | Annotation | Rule |
|------|-----------|------|
| Standard | `TA_CapStd` | Drop/block a job when `#jobs in node ≥ N_std` (`entities_dropped`) |
| Priority | `TA_CapPri` | Drop/block a job when `#jobs in node ≥ N_pri` (`entities_dropped`) |

## Sequence flows

All sequence flows are marked **`instant`** (annotation `TA_Instant`): there is **no
transit delay** between nodes. All time is consumed inside the service Tasks. In a
multi-stage model a flow could instead carry a transit delay; here transfers are
modelled as immediate (`next_queue` is scheduled at the current clock).

## Notes

- The model is **event-driven** (event scheduling): the simulation clock advances from
  one scheduled event to the next (`Simulator` event calendar), not in fixed steps.
- Events: **Arrival**, **Departure** (service completion), **Transfer** (hand-off to the
  next node).
- The two lanes are **modular** queueing nodes and can be chained (`next_queue`) to build
  multi-stage systems in the next session.
