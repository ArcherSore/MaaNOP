# Agent Notes for MaaNOP

MaaFramework automation for the Windows client of 火影忍者 Online.

- Pipeline JSON (`assets/resource/pipeline/`, templates in `assets/resource/image/`) is the default. Add Python in `agent/` only for what the pipeline cannot express: cross-node state, dynamic computation, branching on earlier results.
- Tasks and options exposed to the GUI live in `assets/interface.json`.

## Names Are Interfaces
- Node names are referenced as strings from several places:
  - Python: `get_latest_detail(context, "GetNextServer")`, `run_recognition("FindDownArrow", ...)`, `run_task(...)`, `clear_hit_count(...)`.
  - `reco_login.py` maps task entry names (`AccountLeveling`, ...) to task modes.
  - `interface.json` `pipeline_override` targets node names.
- Before renaming a node, task entry or custom registration name, grep `agent/`, the pipelines and `interface.json`.
- `Leveling.json` is large and tuned against live runs; keep edits local.

## Login
- `AccountLeveling`, `AccountClaims` and `ShoppingFestivalTask` share `Login.json`, then route by task mode. New accounts (leveling) get no login popups; existing accounts always do, so the other modes must pass through popup handling before routing.
- Popup behaviour (measured live):
  - An accepted close click removes the popup within ~0.1s.
  - Clicks made while the game is still loading, or on a popup under another popup's dim mask, are dropped, not queued.
  - Each popup darkens everything below it, but a dimmed lower popup still matches its template (method 5). `LoginPopupAppears` therefore relies on the order of its `popups` list (upper popups first) and re-evaluates after every click.
- Exit only through `LoginScreenClear` (体力 label, method 10001, fails under any mask), checked twice 2s apart.

## Recognition
- Verify every recognition (OCR and template) against real screenshots before relying on it. Do not assume a popup, toast or button always appears, or always looks the same.
- OCR misreads small game text often; prefer TemplateMatch where a stable image exists.
- Do not put OCR nodes with overlapping ROIs in the same `next` list; results get corrupted.
- Set template `threshold` from scores measured on real screenshots, with margin for cross-device rendering differences. Do not copy a number from another node.
- Tiny templates (a digit): crop only the glyph that differs. A whole `0次` crop scored `1次` at 0.83 (vs 1.0 on `0次`); the lone `0` scored `1` at 0.54.
- If a template misses intermittently, the target probably has another state (e.g. hover after a click). Capture it (PrintWindow screenshot) and test against it.
- In `And.all_of`, a node name only borrows that node's recognition params; its `inverse` is ignored. `"recognition": "OtherNode"` is not valid outside `And`. Express "A and not B" as two chained nodes, with `inverse` on the node that tests absence. When both must hold on the same frame (the screen can change between two polls, e.g. a loading screen also hides B), use the `MatchWithout` custom recognition (`reco_common.py`).

## Clicks & Button States
- A pipeline Click lands at a random point inside its target box, so target boxes and template ROIs must lie strictly inside the clickable area. Use `PreciseClick` (pipeline) or `click_center` (Python) when the exact center matters.
- Buttons whose meaning is their colour (orange 领取, blue 扫荡, grey = unavailable) also brighten on hover, and Seize leaves the cursor where the last click was. Find the button with a loose template (`threshold` ~0.7, `sub_name`), then decide its state with a `ColorMatch` on `roi: "<sub_name>"`. Measure pixel counts for every state.
- Text on a button whose background changes (hover, pressed): match with `green_mask` over a text-only crop.
- Modal windows swallow clicks silently while `FindTopEntry` still finds the icon under the dim mask. A click on an entry is only "done" once the target window's own flag is recognized.
- Toasts can outlive the popup that triggered them. When checking for a toast right after another one, give the old one time to fade (`post_delay`; this is one of the accepted delay cases below).

## Pipeline Flow
Adapted from MaaEnd's pipeline guide; MaaNOP keeps its own conventions (`FindTopEntry`, quiet-period checks).

- **Recognize, act, recognize.** `Node.Action.Succeeded` only means the click was sent. After every click that opens, closes, claims, spends or confirms something, the next node must recognize the new state (target window flag, button turned grey, dialog gone) before the flow moves on. Gate irreversible or spending steps (sweeps, resets, purchases) on the previous step's verified state, and cap them with `max_hit`.
- **Do not click again to "make sure".** Re-click only when the recognized state says the target is still pending (still-orange 领取), never because a timer ran out; a second click may land on the next screen.
- **Delays hide missing states.** Prefer an intermediate recognition node or `post_wait_freezes` over `pre_delay`/`post_delay`. A delay is acceptable only where the screen offers no usable signal (a toast animation that never freezes, a row replaced in place by the next tier); say so in a comment.
- **Make `next` complete.** List every expected screen (resume mid-flow, dialogs, loading) so one screenshot hits the right node. A node with no `recognition` always hits: never put it ahead of states that should be tried first.
- **`next` carries the flow; `on_error` is only for recovery.**
  - Normal transitions, completion and "nothing to do" are recognized states in `next` (no orange 领取 twice in a row, reset count 0, window flag gone).
  - `on_error` runs when a node's `next` times out or its action fails. A task that ends through an `on_error` branch reports **Succeeded** (measured: a timed-out wait routed to a terminal node ends with `Tasker.Task.Succeeded`).
  - Use it only when the branch really does something: an alternative route, cleanup, or the keep-waiting pattern (`on_error` pointing at an always-hit node; see `ArenaBattleKeepWaiting`). Never use it just to print a failure message, retry the same action, or turn a failure into a "skip".
- **Let real failures fail.** With no `on_error`, a `next` that times out (or a hit node whose action fails) ends the task as `Tasker.Task.Failed`. The GUI shows that, and the log names the node; that is already the failure report. Do not hide it behind `on_error`, and do not end a failed path in an empty `next` just to show a message.
  - A wait's `timeout` belongs to the node whose `next` is waiting, not to the node being waited for.
  - Deliberate failure, for a *recognized* state that means the user's goal cannot be met (battle lost, a safety `max_hit` reached): end in one terminal node whose action fails (MaaEnd's `FalseAction`; MaaNOP has none yet, so add it to `agent/` the first time it is needed). If the user needs a message, put it on that node as `Node.Action.Failed`. The failed action also sends `Node.PipelineNode.Failed`, but with the `focus` of the predecessor whose `next` hit it, so do not put the reason there too. Do not chain to a never-matching node to force a timeout. "Expected screen never appeared" needs no fail node: the timeout already fails.
- **`focus` is for the user, not for every node** (MaaEnd rule: do not add it unless asked). Add it only where it tells the user something the task status and log do not:
  - Progress on long runs and the outcome: level reached, attempts used up, nothing to claim.
  - A failure the user can act on or should understand (team locked, battle lost, so lower the difficulty). Put it on the node whose `next` is waiting, at the stage the user would recognize (entry not found, window does not open). Do not repeat it on every internal wait (panel did not close, button did not turn grey). If several nodes would get the same text, consolidate it into one message at a meaningful stage boundary when possible; otherwise rely on the task status and log.
  - Say what was observed, not a guessed cause. `Node.PipelineNode.Failed` fires both on a `next` timeout and when the hit node's action fails, so "点了领取但按钮没有变灰" is fine; "网络卡顿" or "次数不足" is not, unless recognized.
  - One cause, one message. Do not add another message on a wrapper node or a `run_task` caller when the inner node already reported. Do not put failure text on a node whose `on_error` recovers (including keep-waiting): `Node.PipelineNode.Failed` is sent before `on_error` runs. Never use `Node.NextList.Failed` (it fires every polling round).
  - `focus` never changes flow or result. Do not add nodes, branches or `on_error` just to produce a nicer message. Use plain-string messages; MaaNOP has no telemetry, so `trace` does nothing.
  - Keep existing messages when editing a node, unless its behaviour changes.
- **`max_hit` is a safety cap, not a loop fix.** If a loop needs it to end, the recognition or logic is wrong; fix that.
- **One ESC, then verify.** Close a window with one ESC whose `next` is an inverse check of the window flag. If the window is still there, the wait times out and the task fails; do not press ESC again, since the second press may land on whatever is underneath.

## Python Actions
- Call maafw APIs directly; do not add helpers that only re-wrap them.
- Express waits as a pipeline sub-task via `context.run_task("Node")` (`next` / `timeout` / `post_delay`), and decide the outcome from the node names in `TaskDetail.nodes`. Do not rely on `status`: it is Failed when a `next` times out with no `on_error`, but Succeeded when an `on_error` branch handled it, so it cannot tell a handled timeout from a clean finish.
- Check `context.tasker.stopping` after each blocking call.

## Validation
CI (`.github/workflows/check.yml`) runs:
- `npx @nekosu/maa-tools check`. **Leave this to CI**: a local run on Windows deleted the tracked images under `assets/resource/image/` (recover with `git restore`).
- `python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`. Pipeline files contain `//` comments, so plain `json.loads` fails on them.

CI does not catch everything. Locally:
1. After editing `agent/`, run `python -m compileall agent` (CI does not check Python).
2. After editing pipelines, load the bundle with the project's `.venv` maafw (`Resource.post_bundle` is enough). `validate_schema.py` misses a `next` / `on_error` naming a missing node, or a node name used as `recognition` outside `And`, and the engine refuses to load the whole resource for either.
3. Run the changed task against a fake `CustomController` that serves saved screenshots and switches frame on click (a click-to-state table). Cover "click lost", "state did not change" and "screen refreshes late".
4. Run spending or irreversible steps on the real game only after checking the current screen and getting approval.
