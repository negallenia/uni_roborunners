"""
pyExecutor.py — Default naive Python Executor.

process_new_plan pushes all plan actions to staged, truncates to 10,
and propagates the terminal state from the agent's current location.
"""
"""
import MAPF
import random

MAX_STAGED = 10
DELTA = {0: 1, 1: None, 2: -1, 3: None}  # filled in initialize

class pyExecutor:
    def __init__(self):
        self.env = None

    def initialize(self, preprocess_time_limit: int):
        DELTA[1] = self.env.cols
        DELTA[3] = -self.env.cols

    def process_new_plan(self, sync_time_limit: int, plan, staged_actions) -> list:
        # Push all plan actions, then truncate to MAX_STAGED
        for i in range(len(plan.actions)):
            for a in plan.actions[i]:
                staged_actions[i].append(a)
            if len(staged_actions[i]) > MAX_STAGED:
                del staged_actions[i][MAX_STAGED:]

        # Propagate terminal state from current location through staged actions
        predicted = []
        cols = self.env.cols
        rows = self.env.rows
        env_map = self.env.map
        for i in range(self.env.num_of_agents):
            loc = self.env.curr_states[i].location
            ori = self.env.curr_states[i].orientation
            for a in staged_actions[i]:
                if a == MAPF.Action.FW:
                    nxt = loc + DELTA[ori]
                    nr, nc = divmod(nxt, cols)
                    if 0 <= nr < rows and 0 <= nc < cols and env_map[nxt] == 0:
                        loc = nxt
                elif a == MAPF.Action.CR:
                    ori = (ori + 1) % 4
                elif a == MAPF.Action.CCR:
                    ori = (ori + 3) % 4
            predicted.append(MAPF.State(loc, -1, ori))
        return predicted

    def next_command(self, exec_time_limit: int) -> list:
        return [
            random.choice([MAPF.ExecutionCommand.GO, MAPF.ExecutionCommand.STOP])
            for _ in range(self.env.num_of_agents)
        ]
"""

#Delay-aware executor for the Python interface.


import MAPF
MAX_STAGED = 4

class pyExecutor:
    def __init__(self):
        self.env = None

    def initialize(self, preprocess_time_limit: int):
        pass

    def process_new_plan(self, sync_time_limit: int, plan, staged_actions) -> list:
        num_agents = self.env.num_of_agents
        if len(plan.actions) != num_agents or len(staged_actions) != num_agents:
            raise ValueError("Plan and staged actions must contain one entry per agent")

        action_time = max(1, self.env.action_time)
        max_counter = max(1, self.env.max_counter)
        stage_limit = max(
            1,
            min(
                MAX_STAGED,
                self.env.min_planner_communication_time
                // (action_time * max_counter)
                + 1,
            ),
        )

        for agent in range(num_agents):
            queue = staged_actions[agent]
            index = 0
            while index < len(queue):
                if queue[index] in (MAPF.Action.W, MAPF.Action.NA):
                    del queue[index]
                else:
                    index += 1
            if len(queue) > stage_limit:
                del queue[stage_limit:]
            for action in plan.actions[agent]:
                if len(queue) >= stage_limit:
                    break
                if action not in (MAPF.Action.W, MAPF.Action.NA):
                    queue.append(action)
        states = [self._state_dict(state) for state in self.env.system_states]
        queues = [list(staged_actions[agent]) for agent in range(num_agents)]
        accepted_lengths = [0] * num_agents
        horizon = max(
            1,
            (self.env.min_planner_communication_time + action_time - 1)
            // action_time,
        )

        for tick in range(horizon):
            if not any(queues) and not any(state["in_delay"] for state in states):
                for state in states:
                    state["timestep"] += horizon - tick
                break

            orders = self._visit_orders(states, queues)
            allowed = self._allowed_moves(states, queues, orders)
            for agent in range(num_agents):
                if allowed[agent] and queues[agent]:
                    action_index = len(staged_actions[agent]) - len(queues[agent])
                    accepted_lengths[agent] = max(
                        accepted_lengths[agent], action_index + 1
                    )
                self._advance(states[agent], queues[agent], allowed[agent])
                states[agent]["timestep"] += 1

        for agent in range(num_agents):
            queue = staged_actions[agent]
            if len(queue) > accepted_lengths[agent]:
                del queue[accepted_lengths[agent]:]

        predicted = []
        for state in states:
            result = MAPF.State(
                state["location"], state["timestep"], state["orientation"]
            )
            result.counter.count = state["count"]
            result.counter.maxCount = state["max_count"]
            result.delay.minDelay = state["min_delay"]
            result.delay.maxDelay = state["max_delay"]
            result.delay.inDelay = state["in_delay"]
            predicted.append(result)
        return predicted

    def _state_dict(self, state):
        return {
            "location": state.location,
            "orientation": state.orientation,
            "count": state.counter.count,
            "max_count": max(1, state.counter.maxCount),
            "timestep": state.timestep,
            "min_delay": state.delay.minDelay,
            "max_delay": state.delay.maxDelay,
            "in_delay": state.delay.inDelay,
        }

    def _forward_location(self, location: int, orientation: int):
        row, col = divmod(location, self.env.cols)
        if orientation == 0:
            col += 1
        elif orientation == 1:
            row += 1
        elif orientation == 2:
            col -= 1
        elif orientation == 3:
            row -= 1
        else:
            return None

        if not (0 <= row < self.env.rows and 0 <= col < self.env.cols):
            return None
        destination = row * self.env.cols + col
        return destination if self.env.map[destination] == 0 else None

    def _visit_orders(self, states, queues):
        orders = {}
        locations = []
        orientations = []

        for agent, state in enumerate(states):
            locations.append(state["location"])
            orientations.append(state["orientation"])
            orders.setdefault(state["location"], []).append(agent)

        max_actions = max((len(queue) for queue in queues), default=0)
        invalid_route = [False] * len(states)
        for action_index in range(max_actions):
            for agent, queue in enumerate(queues):
                if invalid_route[agent] or action_index >= len(queue):
                    continue
                action = queue[action_index]
                if action == MAPF.Action.FW:
                    destination = self._forward_location(
                        locations[agent], orientations[agent]
                    )
                    if destination is None:
                        invalid_route[agent] = True
                        continue
                    orders.setdefault(destination, []).append(agent)
                    locations[agent] = destination
                elif action == MAPF.Action.CR:
                    orientations[agent] = (orientations[agent] + 1) % 4
                elif action == MAPF.Action.CCR:
                    orientations[agent] = (orientations[agent] + 3) % 4
        return orders

    def _allowed_moves(self, states, queues, orders):
        allowed = [False] * len(states)
        for agent, state in enumerate(states):
            if state["in_delay"] or not queues[agent]:
                continue
            if queues[agent][0] != MAPF.Action.FW:
                allowed[agent] = True
                continue

            destination = self._forward_location(
                state["location"], state["orientation"]
            )
            if destination is None:
                continue
            visitors = orders.get(destination)
            allowed[agent] = not visitors or visitors[0] == agent
        return allowed

    def _advance(self, state, queue, allowed):
        if state["in_delay"]:
            state["in_delay"] = False
            return
        if not allowed or not queue:
            return

        action = queue[0]
        if action in (MAPF.Action.W, MAPF.Action.NA):
            queue.pop(0)
            return

        state["count"] += 1
        if state["count"] < state["max_count"]:
            return

        state["count"] = 0
        if action == MAPF.Action.FW:
            destination = self._forward_location(
                state["location"], state["orientation"]
            )
            if destination is not None:
                state["location"] = destination
        elif action == MAPF.Action.CR:
            state["orientation"] = (state["orientation"] + 1) % 4
        elif action == MAPF.Action.CCR:
            state["orientation"] = (state["orientation"] + 3) % 4
        queue.pop(0)

    def next_command(self, exec_time_limit: int) -> list:
        states = [self._state_dict(state) for state in self.env.system_states]
        queues = [
            self.env.staged_actions[agent] for agent in range(len(states))
        ]
        orders = self._visit_orders(states, queues)
        allowed = self._allowed_moves(states, queues, orders)
        return [
            MAPF.ExecutionCommand.GO if can_go else MAPF.ExecutionCommand.STOP
            for can_go in allowed
        ]
